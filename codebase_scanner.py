"""
codebase_scanner.py
--------------------
GovernAI Codebase Scanner

Walks a target Python project, statically analyzes it (via `ast`, not regex),
and extracts governance-relevant signals: ML framework/model type, hyperparameters,
data sources, and sensitive-data indicators. Builds a payload and posts it to the
existing GovernAI Intake API (POST /api/v1/scanner/intake), reusing the same
plug-and-play pipeline that resume_screener_app.py already uses.

Design principle (per Mebin's "verifier" note): nothing is auto-confirmed.
Every detected attribute carries a `confidence` score and a `status` of
"detected_unverified". A human reviews and flips it to "verified" in the
dashboard before it's treated as ground truth compliance evidence.

Usage:
    python codebase_scanner.py /path/to/target/project \
        --system-name "HR Resume Screener" \
        --owner "Grishma" \
        --business-purpose "Screens resumes for HR shortlisting" \
        --intake-url http://localhost:8000/api/v1/scanner/intake \
        --dry-run          # skip the POST, just print/save the report

Payload sent matches the real ScannerPayload schema from server.py:
    system_metadata { name, owner, business_purpose, model_type, model_vendor, model_source }
    raw_prediction   (omitted — this scanner does static analysis, not inference)
    compliance_evidence  (list of detections, each flagged "detected_unverified")

Output:
    - Prints a human-readable detection report to stdout
    - Saves the same report as JSON to ./scan_report_<system_name>.json
    - POSTs to the intake endpoint unless --dry-run is set
"""

import argparse
import ast
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Known signal tables — extend these as you encounter more patterns in Beinex apps
# ---------------------------------------------------------------------------

FRAMEWORK_IMPORTS = {
    "sklearn": "scikit-learn",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "transformers": "HuggingFace Transformers",
    "openai": "OpenAI API",
    "anthropic": "Anthropic API",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "langchain": "LangChain",
}

# Model constructor call names we recognize -> treated as "model instantiation" evidence
MODEL_CONSTRUCTOR_HINTS = {
    "RandomForestClassifier", "RandomForestRegressor", "LogisticRegression",
    "XGBClassifier", "XGBRegressor", "LGBMClassifier",
    "AutoModel", "AutoModelForCausalLM", "AutoModelForSequenceClassification",
    "ChatOpenAI", "OpenAI", "Anthropic", "ChatAnthropic",
    "Sequential", "Model",  # keras/tf generic
}

# Kwargs on model constructors / config dicts we treat as "hyperparameters"
HYPERPARAM_KEYS = {
    "n_estimators", "max_depth", "learning_rate", "temperature", "top_p",
    "epochs", "batch_size", "num_train_epochs", "lr", "hidden_size",
    "num_layers", "dropout", "random_state", "max_tokens", "n_neighbors",
}

# Function/attribute calls that indicate reading a data source
DATA_SOURCE_CALLS = {
    "read_csv": "CSV file (pandas)",
    "read_excel": "Excel file (pandas)",
    "read_sql": "SQL query (pandas)",
    "read_json": "JSON file (pandas)",
    "open": "Local file",
    "get": "HTTP GET (requests) — possible external data source",
    "connect": "Database connection",
    "create_engine": "SQLAlchemy DB engine",
}

# Keywords in string literals / identifiers that hint at sensitive data categories
SENSITIVE_KEYWORDS = {
    "ssn", "social_security", "pii", "email", "phone", "address",
    "date_of_birth", "dob", "salary", "health", "medical", "diagnosis",
    "credit_score", "credit_card", "ethnicity", "race", "gender",
    "religion", "resume", "candidate", "applicant",
}

# --- Signals that map directly to compliance_svc.auto_populate_compliance()'s
# --- real evidence dict keys: {"documentation_url", "human_in_loop", "privacy_filters"}
# --- These are HINTS ONLY — the scanner never sets these True on its own.
# --- A human has to confirm via --confirm-privacy-filters / --confirm-human-in-loop
# --- after reviewing the hint list, per Mebin's verifier requirement.

PRIVACY_FILTER_HINT_NAMES = {
    "kiji", "presidio", "scrubadub", "anonymize", "mask_pii",
    "redact_pii", "pii_mask", "mask_text", "redact",
}

HUMAN_IN_LOOP_HINT_NAMES = {
    "approve", "reject", "human_review", "manual_override",
    "requires_approval", "confirm_decision", "reviewer_signoff",
}


@dataclass
class Detection:
    category: str          # "framework" | "hyperparameter" | "data_source" | "sensitive_data"
    value: str
    file: str
    line: int
    confidence: float      # 0.0 - 1.0
    status: str = "detected_unverified"


@dataclass
class ScanResult:
    system_name: str
    scanned_path: str
    scanned_at: str
    files_scanned: int
    detections: list = field(default_factory=list)

    def to_intake_payload(self, owner: str, business_purpose: str,
                           documentation_url: str | None,
                           confirm_privacy_filters: bool,
                           confirm_human_in_loop: bool) -> dict:
        """
        Shape this into the real ScannerPayload contract confirmed from server.py + compliance_svc.py:

            ScannerPayload {
                system_metadata: { name, owner, business_purpose,
                                    model_type, model_vendor, model_source },
                raw_prediction: <single prediction object, optional>,
                compliance_evidence: dict with EXACTLY these keys, per auto_populate_compliance():
                    "documentation_url": str
                    "human_in_loop": bool
                    "privacy_filters": bool
            }

        This scanner does static analysis only (no inference calls), so raw_prediction
        is omitted. owner/business_purpose can't be inferred from code, so they come
        from CLI args.

        IMPORTANT: privacy_filters and human_in_loop are only set True if the caller
        explicitly passes --confirm-privacy-filters / --confirm-human-in-loop. The
        scanner only *detects hints* (e.g. a "kiji" import, an "approve" function) —
        it never sets these True on its own. Run once without the confirm flags,
        review the evidence_hint section of the report, then re-run with the
        confirm flags once a human has actually verified it. This is the "verifier"
        step Mebin asked for.
        """
        frameworks = [d for d in self.detections if d.category == "framework"]
        primary_framework = frameworks[0].value if frameworks else "Unknown"

        privacy_hints = [d for d in self.detections if d.category == "evidence_hint:privacy_filters"]
        human_loop_hints = [d for d in self.detections if d.category == "evidence_hint:human_in_loop"]

        return {
            "system_metadata": {
                "name": self.system_name,
                "owner": owner,
                "business_purpose": business_purpose,
                "model_type": primary_framework,
                "model_vendor": "Detected via static analysis",
                "model_source": f"codebase_scanner ({self.scanned_path})",
            },
            "raw_prediction": None,  # no inference performed by this scanner
            "compliance_evidence": {
                "documentation_url": documentation_url or "",
                "human_in_loop": bool(confirm_human_in_loop and human_loop_hints),
                "privacy_filters": bool(confirm_privacy_filters and privacy_hints),
            },
        }


class CodebaseScanner:
    def __init__(self, target_path: str, system_name: str):
        self.target_path = Path(target_path)
        self.system_name = system_name
        self.detections: list[Detection] = []
        self.files_scanned = 0

    def scan(self) -> ScanResult:
        for py_file in self.target_path.rglob("*.py"):
            # skip venvs / caches / migrations noise
            if any(part in {".venv", "venv", "__pycache__", "node_modules", ".git",
                            ".cache", "site-packages", "dist", "build"}
                   for part in py_file.parts):
                continue
            self._scan_file(py_file)
            self.files_scanned += 1

        return ScanResult(
            system_name=self.system_name,
            scanned_path=str(self.target_path),
            scanned_at=datetime.now(timezone.utc).isoformat(),
            files_scanned=self.files_scanned,
            detections=self.detections,
        )

    def _scan_file(self, path: Path) -> None:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            return  # skip unparsable files rather than crash the whole scan

        rel = str(path.relative_to(self.target_path))

        for node in ast.walk(tree):
            self._check_imports(node, rel)
            self._check_model_calls(node, rel)
            self._check_data_source_calls(node, rel)
            self._check_sensitive_identifiers(node, rel)
            self._check_evidence_hints(node, rel)

    # -- individual checks ---------------------------------------------------

    def _check_imports(self, node: ast.AST, file: str) -> None:
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = [node.module.split(".")[0]]

        for mod in modules:
            if mod in FRAMEWORK_IMPORTS:
                self.detections.append(Detection(
                    category="framework",
                    value=FRAMEWORK_IMPORTS[mod],
                    file=file,
                    line=node.lineno,
                    confidence=0.95,  # an import is near-certain evidence
                ))

    def _check_model_calls(self, node: ast.AST, file: str) -> None:
        if not isinstance(node, ast.Call):
            return
        func_name = self._call_name(node)
        if func_name in MODEL_CONSTRUCTOR_HINTS:
            self.detections.append(Detection(
                category="framework",
                value=f"Model instantiation: {func_name}",
                file=file,
                line=node.lineno,
                confidence=0.85,
            ))
            # pull keyword args that look like hyperparameters
            for kw in node.keywords:
                if kw.arg in HYPERPARAM_KEYS:
                    val = self._literal_or_placeholder(kw.value)
                    self.detections.append(Detection(
                        category="hyperparameter",
                        value=f"{kw.arg}={val} (via {func_name})",
                        file=file,
                        line=node.lineno,
                        confidence=0.8,
                    ))

    def _check_data_source_calls(self, node: ast.AST, file: str) -> None:
        if not isinstance(node, ast.Call):
            return
        func_name = self._call_name(node)
        if func_name in DATA_SOURCE_CALLS:
            self.detections.append(Detection(
                category="data_source",
                value=DATA_SOURCE_CALLS[func_name],
                file=file,
                line=node.lineno,
                confidence=0.6,  # lower — e.g. open() is generic, could be a log file not data
            ))

    def _check_sensitive_identifiers(self, node: ast.AST, file: str) -> None:
        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            name = node.value
        elif isinstance(node, ast.Attribute):
            name = node.attr

        if not name:
            return
        lowered = name.lower()
        for kw in SENSITIVE_KEYWORDS:
            if kw in lowered:
                self.detections.append(Detection(
                    category="sensitive_data",
                    value=kw,
                    file=file,
                    line=getattr(node, "lineno", 0),
                    confidence=0.5,  # string/identifier match is weak signal, needs human review
                ))
                break

    def _check_evidence_hints(self, node: ast.AST, file: str) -> None:
        """
        Looks for signals matching the two boolean evidence keys that
        auto_populate_compliance() actually checks: privacy_filters and human_in_loop.
        Checked against imports, function calls, and attribute access names.
        """
        names_to_check = []
        if isinstance(node, ast.Import):
            names_to_check = [alias.name.split(".")[0].lower() for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names_to_check = [node.module.split(".")[0].lower()]
        elif isinstance(node, ast.Call):
            fname = self._call_name(node)
            if fname:
                names_to_check = [fname.lower()]
        elif isinstance(node, ast.Name):
            names_to_check = [node.id.lower()]

        for name in names_to_check:
            if any(hint in name for hint in PRIVACY_FILTER_HINT_NAMES):
                self.detections.append(Detection(
                    category="evidence_hint:privacy_filters",
                    value=name,
                    file=file,
                    line=getattr(node, "lineno", 0),
                    confidence=0.6,
                ))
            if any(hint in name for hint in HUMAN_IN_LOOP_HINT_NAMES):
                self.detections.append(Detection(
                    category="evidence_hint:human_in_loop",
                    value=name,
                    file=file,
                    line=getattr(node, "lineno", 0),
                    confidence=0.6,
                ))

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _call_name(node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    @staticmethod
    def _literal_or_placeholder(node: ast.AST) -> str:
        try:
            return repr(ast.literal_eval(node))
        except (ValueError, TypeError):
            return "<dynamic>"


def dedupe(detections: list[Detection]) -> list[Detection]:
    """Collapse duplicate (category, value) hits down to the highest-confidence, first-seen line."""
    seen: dict[tuple, Detection] = {}
    for d in detections:
        key = (d.category, d.value)
        if key not in seen or d.confidence > seen[key].confidence:
            seen[key] = d
    return list(seen.values())


def post_to_intake(payload: dict, intake_url: str) -> None:
    try:
        resp = requests.post(intake_url, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"\n✅ Posted to intake API ({intake_url}) — status {resp.status_code}")
        print(resp.text[:500])
    except requests.RequestException as e:
        print(f"\n⚠️  Could not reach intake API at {intake_url}: {e}")
        print("Report was still saved locally — you can POST it manually once the API is up.")


def print_report(result: ScanResult) -> None:
    print(f"\n=== GovernAI Codebase Scan: {result.system_name} ===")
    print(f"Path: {result.scanned_path}")
    print(f"Files scanned: {result.files_scanned}")
    print(f"Scanned at: {result.scanned_at}\n")

    by_cat: dict[str, list[Detection]] = {}
    for d in result.detections:
        by_cat.setdefault(d.category, []).append(d)

    for cat in ("framework", "hyperparameter", "data_source", "sensitive_data",
                "evidence_hint:privacy_filters", "evidence_hint:human_in_loop"):
        items = by_cat.get(cat, [])
        if not items:
            continue
        print(f"[{cat.upper()}] ({len(items)} detected, unverified)")
        for d in items:
            print(f"  - {d.value}  ({d.file}:{d.line}, confidence={d.confidence})")
        print()

    priv = by_cat.get("evidence_hint:privacy_filters", [])
    loop = by_cat.get("evidence_hint:human_in_loop", [])
    if priv:
        print("→ privacy_filters hint found. If you've verified this is real PII masking,")
        print("  re-run with --confirm-privacy-filters to send it as compliance evidence.\n")
    if loop:
        print("→ human_in_loop hint found. If you've verified there's a real manual review step,")
        print("  re-run with --confirm-human-in-loop to send it as compliance evidence.\n")


def main():
    parser = argparse.ArgumentParser(description="GovernAI Codebase Scanner")
    parser.add_argument("path", help="Path to the target project to scan")
    parser.add_argument("--system-name", required=True, help="Name to register this system as in GovernAI")
    parser.add_argument("--owner", default="Unassigned",
                         help="System owner (can't be inferred from code — required by system_metadata)")
    parser.add_argument("--business-purpose", default="Auto-registered via codebase scanner (needs review)",
                         help="Business purpose (can't be inferred from code — required by system_metadata)")
    parser.add_argument("--intake-url", default="http://localhost:8000/api/v1/scanner/intake")
    parser.add_argument("--documentation-url", default=None,
                         help="Link to system documentation, if any (maps to compliance_evidence.documentation_url)")
    parser.add_argument("--confirm-privacy-filters", action="store_true",
                         help="Only set after a human has verified the detected privacy_filters hint is real")
    parser.add_argument("--confirm-human-in-loop", action="store_true",
                         help="Only set after a human has verified the detected human_in_loop hint is real")
    parser.add_argument("--dry-run", action="store_true", help="Skip POST, just print/save report")
    args = parser.parse_args()

    if not os.path.isdir(args.path):
        print(f"Error: {args.path} is not a directory", file=sys.stderr)
        sys.exit(1)

    scanner = CodebaseScanner(args.path, args.system_name)
    result = scanner.scan()
    result.detections = dedupe(result.detections)

    print_report(result)

    # Full detection detail (frameworks, hyperparams, data sources, sensitive
    # keywords, evidence hints) saved locally for audit/dashboard review —
    # ScannerPayload.compliance_evidence has no room for this level of detail,
    # it only takes the 3 keys auto_populate_compliance() checks.
    full_report_file = f"scan_report_full_{args.system_name.replace(' ', '_')}.json"
    with open(full_report_file, "w") as f:
        json.dump([asdict(d) for d in result.detections], f, indent=2)
    print(f"Saved full detection detail: {full_report_file}")

    payload = result.to_intake_payload(
        owner=args.owner,
        business_purpose=args.business_purpose,
        documentation_url=args.documentation_url,
        confirm_privacy_filters=args.confirm_privacy_filters,
        confirm_human_in_loop=args.confirm_human_in_loop,
    )
    payload_file = f"scan_payload_{args.system_name.replace(' ', '_')}.json"
    with open(payload_file, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Saved API payload: {payload_file}")

    if not args.dry_run:
        post_to_intake(payload, args.intake_url)
    else:
        print("(--dry-run set, skipping POST)")


if __name__ == "__main__":
    main()
