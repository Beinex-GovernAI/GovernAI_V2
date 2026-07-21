"""
test_batch_drift_bias.py
-------------------------
Quick end-to-end test for the new batch-based drift (PSI) and bias
(confidence-gap) functions wired into POST /api/v1/scanner/intake.

Instead of manually running resume_screener_app.py 30+ times to fill the
raw_predictions window, this fires synthetic predictions straight at the
intake endpoint for one system:

  Phase 1 ("baseline"): 15 predictions with confidence scores clustered
  tightly around ~0.85 — simulates a stable, well-behaved model.

  Phase 2 ("drifted"): 15 more predictions with confidence scores shifted
  down and spread wider (~0.55, more variance) — simulates the model's
  output distribution actually shifting, which PSI should pick up on.

After phase 1, drift/bias should look calm. After phase 2, PSI-based drift
should visibly jump since the confidence distribution changed shape, not
just its average.

This exercises BOTH sides of /scanner/intake in one run:
  - raw_prediction (RawPredictionPayload) -> feeds the batch drift/bias functions
  - compliance_evidence (documentation_url, human_in_loop, privacy_filters) ->
    feeds auto_populate_compliance(), same as the codebase scanner does

Usage:
    python test_batch_drift_bias.py --system-name "HR Resume Screener" \
        --owner "Grishma" --business-purpose "Screens resumes for HR shortlisting" \
        --confirm-privacy-filters \
        --intake-url http://localhost:8000/api/v1/scanner/intake

After running, check:
  1. The GovernAI monitoring dashboard for this system — Drift/Bias values
     should show a jump after phase 2 posts.
  2. The compliance tab — controls matching whatever you confirmed
     (e.g. privacy_filters) should show as met, evidence-linked to this test.
  3. The Supabase raw_predictions table — should show ~30 rows for this
     system_id (it keeps the last 30, per your note).
  4. Audit trail — should show repeated "Drift"/"Bias" metric ingestion
     entries with is_breached flipping to true if your threshold is crossed,
     plus compliance control update entries.
"""

import argparse
import random
import time

import requests


def build_payload(system_name: str, owner: str, business_purpose: str,
                   input_text: str, output_text: str, confidence: float,
                   compliance_evidence: dict) -> dict:
    return {
        "system_metadata": {
            "name": system_name,
            "owner": owner,
            "business_purpose": business_purpose,
            "model_type": "OpenAI API",
            "model_vendor": "OpenAI",
            "model_source": "test_batch_drift_bias.py (synthetic)",
        },
        "raw_prediction": {
            "input_text": input_text,
            "output_text": output_text,
            "confidence_score": confidence,
            "metadata": {"synthetic": True},
        },
        "compliance_evidence": compliance_evidence,
    }


def send_batch(intake_url: str, system_name: str, owner: str, business_purpose: str,
               label: str, confidences: list, decisions: list, compliance_evidence: dict) -> None:
    print(f"\n--- Sending {label} batch ({len(confidences)} predictions) ---")
    for i, conf in enumerate(confidences):
        decision = random.choice(decisions)
        payload = build_payload(
            system_name, owner, business_purpose,
            input_text=f"Synthetic resume #{i} for {label} batch",
            output_text=decision,
            confidence=round(conf, 3),
            compliance_evidence=compliance_evidence,
        )
        try:
            resp = requests.post(intake_url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            print(f"  [{i+1}/{len(confidences)}] confidence={conf:.2f} decision={decision} "
                  f"-> compliance_status={data.get('compliance_status')}")
        except requests.RequestException as e:
            print(f"  [{i+1}/{len(confidences)}] FAILED: {e}")
            print("  Is the FastAPI server running? (uvicorn api.server:app --reload --port 8000)")
            return
        time.sleep(0.2)  # small pause so timestamps/ordering stay sane


def main():
    parser = argparse.ArgumentParser(description="Test batch drift/bias via scanner_intake")
    parser.add_argument("--system-name", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--business-purpose", required=True)
    parser.add_argument("--intake-url", default="http://localhost:8000/api/v1/scanner/intake")
    parser.add_argument("--documentation-url", default=None,
                         help="Maps to compliance_evidence.documentation_url")
    parser.add_argument("--confirm-privacy-filters", action="store_true",
                         help="Send privacy_filters=True in compliance_evidence")
    parser.add_argument("--confirm-human-in-loop", action="store_true",
                         help="Send human_in_loop=True in compliance_evidence")
    args = parser.parse_args()

    compliance_evidence = {
        "documentation_url": args.documentation_url or "",
        "human_in_loop": args.confirm_human_in_loop,
        "privacy_filters": args.confirm_privacy_filters,
    }
    print(f"Compliance evidence being sent with every request: {compliance_evidence}")

    random.seed(42)  # reproducible run

    # Phase 1: stable baseline — confidence tightly clustered around 0.85
    baseline_confidences = [random.gauss(0.85, 0.03) for _ in range(15)]
    baseline_confidences = [min(max(c, 0.0), 1.0) for c in baseline_confidences]
    send_batch(args.intake_url, args.system_name, args.owner, args.business_purpose,
               "BASELINE", baseline_confidences, ["Shortlisted", "Rejected"], compliance_evidence)

    print("\n>>> Check the dashboard now — drift/bias should look calm, compliance controls "
          "for privacy/human-oversight should show as met if you passed the confirm flags.")
    input(">>> Press Enter to send the DRIFTED batch...")

    # Phase 2: drifted — confidence lower and more spread out
    drifted_confidences = [random.gauss(0.55, 0.15) for _ in range(15)]
    drifted_confidences = [min(max(c, 0.0), 1.0) for c in drifted_confidences]
    send_batch(args.intake_url, args.system_name, args.owner, args.business_purpose,
               "DRIFTED", drifted_confidences, ["Rejected", "Rejected", "Shortlisted"], compliance_evidence)

    print("\n>>> Done. Now check:")
    print("  1. Monitoring dashboard for this system — Drift value should have jumped.")
    print("  2. Compliance tab — controls matching your confirmed evidence should show as met.")
    print("  3. Supabase raw_predictions table — should show up to 30 rows for this system.")
    print("  4. Audit trail — look for Drift/Bias metric entries AND compliance control updates,")
    print("     check is_breached / is_met accordingly.")


if __name__ == "__main__":
    main()
