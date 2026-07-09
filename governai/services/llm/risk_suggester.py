"""High-level orchestration for the LLM-powered Risk Tier Suggestion feature.

This is the module the Streamlit UI (and anything else) should import from.
It wires together, in order:

    pii_pipeline (no-op today, Kiji slots in here later)
        -> prompt_templates (builds the chat messages)
        -> foundry_client (talks to Foundry Local)
        -> prompt_templates (parses the structured response)

into a single `suggest_risk_tier()` call returning a `RiskSuggestion`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .exceptions import LLMRiskAssessmentError
from .foundry_client import FoundryClient, get_default_client
from .pii_pipeline import TextPreprocessor, run_pipeline
from .prompt_templates import build_messages, parse_response


@dataclass
class RiskSuggestion:
    """Structured result of an LLM risk-tier suggestion, ready to render
    directly in the Streamlit UI."""

    eu_ai_act_label: str          # e.g. "High Risk" (the Act's own wording)
    internal_tier: str            # e.g. "High" (GovernAI's risk_tier vocabulary)
    explanation: str
    key_factors: List[str] = field(default_factory=list)
    model_used: str = ""
    discovery_mode: str = ""      # "sdk-auto-discovered" or "static-env-fallback"
    raw_response: str = ""
    masked_text: str = ""

    def as_dict(self) -> dict:
        return {
            "eu_ai_act_label": self.eu_ai_act_label,
            "internal_tier": self.internal_tier,
            "explanation": self.explanation,
            "key_factors": self.key_factors,
            "model_used": self.model_used,
            "discovery_mode": self.discovery_mode,
        }


def suggest_risk_tier(
    system_description: str,
    *,
    preprocessors: Optional[List[TextPreprocessor]] = None,
    client: Optional[FoundryClient] = None,
) -> RiskSuggestion:
    """Suggests an EU AI Act risk tier for a plain-language AI system
    description, using the configured local LLM via Foundry Local.

    Args:
        system_description: Plain-language description of the AI system.
        preprocessors: Optional list of text-preprocessing steps (e.g. a
            future PII-masking step) run on the description before it is
            sent to the model. Defaults to `pii_pipeline.DEFAULT_PREPROCESSORS`
            (currently a no-op).
        client: Optional `FoundryClient` instance. Defaults to a shared,
            lazily-connected client using the configured default model alias.

    Returns:
        A `RiskSuggestion` with the suggested tier, explanation, and the
        contributing factors the model identified.

    Raises:
        ValueError: if `system_description` is empty/blank.
        FoundryConnectionError: Foundry Local's service could not be reached.
        FoundryModelError: the service responded but inference failed.
        LLMResponseParseError: the model's response couldn't be parsed into
            a valid structured suggestion.
    """
    if not system_description or not system_description.strip():
        raise ValueError("system_description must be a non-empty string.")

    text = run_pipeline(system_description, preprocessors)

    active_client = client or get_default_client()
    messages = build_messages(text)
    raw_response = active_client.chat_completion(messages)
    parsed = parse_response(raw_response)

    return RiskSuggestion(
        eu_ai_act_label=parsed["eu_ai_act_label"],
        internal_tier=parsed["internal_tier"],
        explanation=parsed["explanation"],
        key_factors=parsed["key_factors"],
        model_used=active_client.model_id,
        discovery_mode=active_client.connection_info.discovery_mode,
        raw_response=raw_response,
        masked_text=text,
    )
