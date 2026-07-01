"""Prompt construction and structured-response parsing for the
LLM-powered Risk Tier Suggestion feature.

Tier vocabulary note
---------------------
The EU AI Act itself names four tiers: Unacceptable, High, Limited, and
Minimal Risk. GovernAI's existing data model (`AISystem.risk_tier`,
`risk_svc.py`) instead stores the unacceptable tier as `"Prohibited"`
(see `risk_svc.py`'s comment: "matches AISystem.risk_tier vocabulary").

To keep this feature consistent with the rest of the app while still
speaking the Act's own terms in the explanation shown to the user, the
model is asked for the EU AI Act label, and `TIER_LABEL_TO_INTERNAL` maps
it to GovernAI's internal vocabulary (`Prohibited` / `High` / `Limited` /
`Minimal`) so the suggestion can slot directly next to the questionnaire's
output wherever needed.
"""

from __future__ import annotations

import json
import re

from .exceptions import LLMResponseParseError

# EU AI Act canonical labels, in the exact words used in the Act.
EU_AI_ACT_TIERS = ["Unacceptable Risk", "High Risk", "Limited Risk", "Minimal Risk"]

# Maps the model's EU AI Act label to GovernAI's internal risk_tier vocabulary.
TIER_LABEL_TO_INTERNAL = {
    "Unacceptable Risk": "Prohibited",
    "High Risk": "High",
    "Limited Risk": "Limited",
    "Minimal Risk": "Minimal",
}

SYSTEM_PROMPT = """You are an EU AI Act compliance assistant embedded in an AI governance \
platform. You read a short, plain-language description of an AI system and suggest which \
EU AI Act risk tier it most likely falls under.

The four tiers, in order of severity, are:
- "Unacceptable Risk": systems using subliminal/manipulative techniques, social scoring \
by public authorities, or real-time remote biometric identification by law enforcement in \
public spaces. These are banned outright under Article 5.
- "High Risk": systems listed in Annex III, e.g. used in employment (recruitment, \
performance/termination evaluation), education/vocational access, critical infrastructure \
safety components, essential private/public services (credit scoring, benefits eligibility, \
insurance pricing), law enforcement risk assessment, migration/asylum/border control, or \
judicial/democratic processes. Also biometric categorization or emotion recognition.
- "Limited Risk": systems with transparency obligations under Article 50, e.g. chatbots that \
interact directly with people, or systems generating synthetic audio/image/video/text \
content (deepfakes), where people must be informed they're interacting with AI or that \
content is AI-generated.
- "Minimal Risk": everything else (e.g. spam filters, internal scheduling tools, recommender \
systems with no Annex III use-case and no direct end-user-facing generative/chat component).

This is a preliminary, advisory suggestion only -- it does not replace the formal \
questionnaire-based assessment elsewhere in this platform, and a human must confirm the \
final tier.

Respond with ONLY a single JSON object (no markdown fences, no extra commentary) with \
exactly these keys:
{
  "risk_tier": one of "Unacceptable Risk", "High Risk", "Limited Risk", "Minimal Risk",
  "explanation": a 2-4 sentence plain-language explanation of why,
  "key_factors": an array of 1-5 short strings naming the specific facts in the \
description that drove the classification
}"""


def build_messages(system_description: str) -> list[dict]:
    """Builds the chat messages sent to the model for a given plain-language
    AI system description."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "AI system description:\n"
                f"\"\"\"\n{system_description.strip()}\n\"\"\"\n\n"
                "Respond with only the JSON object described in your instructions."
            ),
        },
    ]


def _extract_json_object(raw_text: str) -> dict:
    """Best-effort extraction of a JSON object from the model's raw output.

    Local/small models occasionally wrap JSON in markdown code fences or add
    a stray sentence before/after it, even when instructed not to. This
    tries a direct parse first, then falls back to extracting the first
    `{...}` block found in the text.
    """
    text = raw_text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise LLMResponseParseError(
        "The model's response was not valid JSON and no JSON object could be "
        f"recovered from it. Raw response started with: {text[:200]!r}"
    )


def parse_response(raw_text: str) -> dict:
    """Parses and validates the model's raw text into a normalized dict with
    keys: eu_ai_act_label, internal_tier, explanation, key_factors.

    Raises:
        LLMResponseParseError: if the response isn't valid/parseable JSON,
            is missing required keys, or names a tier outside the EU AI Act
            vocabulary.
    """
    data = _extract_json_object(raw_text)

    if not isinstance(data, dict):
        raise LLMResponseParseError(f"Expected a JSON object, got: {type(data).__name__}")

    tier_label = str(data.get("risk_tier", "")).strip()
    # Be lenient about near-matches (e.g. "High" instead of "High Risk").
    normalized_label = next(
        (label for label in EU_AI_ACT_TIERS if label.lower().startswith(tier_label.lower())
         or tier_label.lower().startswith(label.lower().replace(" risk", ""))),
        None,
    )
    if normalized_label is None:
        raise LLMResponseParseError(
            f"Model returned an unrecognized risk tier: {tier_label!r}. "
            f"Expected one of {EU_AI_ACT_TIERS}."
        )

    explanation = str(data.get("explanation", "")).strip()
    if not explanation:
        raise LLMResponseParseError("Model response was missing a non-empty 'explanation'.")

    key_factors = data.get("key_factors", [])
    if not isinstance(key_factors, list):
        key_factors = [str(key_factors)]
    key_factors = [str(f).strip() for f in key_factors if str(f).strip()]

    return {
        "eu_ai_act_label": normalized_label,
        "internal_tier": TIER_LABEL_TO_INTERNAL[normalized_label],
        "explanation": explanation,
        "key_factors": key_factors,
    }
