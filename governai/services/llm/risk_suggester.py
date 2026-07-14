"""High-level orchestration for the LLM-powered Risk Tier Suggestion feature.

This is the module the Streamlit UI (and anything else) should import from.
It wires together, in order:

    pii_pipeline (no-op today, Kiji slots in here later)
        -> prompt_templates (builds the chat messages)
        -> foundry_client (talks to Foundry Local)
        -> prompt_templates (parses the structured response)

into a single `suggest_risk_tier()` call returning a `RiskSuggestion`.

If Foundry Local is unreachable or fails to run the model (e.g. an
Out-Of-Memory error on lower-RAM machines), this falls back to OpenAI's
API automatically, using the same prompt/messages and the same response
parsing, so callers get an identical RiskSuggestion shape either way.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

from .exceptions import FoundryConnectionError, FoundryModelError, LLMRiskAssessmentError
from .foundry_client import FoundryClient, get_default_client
from .pii_pipeline import TextPreprocessor, run_pipeline
from .prompt_templates import build_messages, parse_response

OPENAI_FALLBACK_MODEL = "gpt-4o-mini"
OPENAI_FALLBACK_TIMEOUT_SECONDS = 15


@dataclass
class RiskSuggestion:
    """Structured result of an LLM risk-tier suggestion, ready to render
    directly in the Streamlit UI."""

    eu_ai_act_label: str          # e.g. "High Risk" (the Act's own wording)
    internal_tier: str            # e.g. "High" (GovernAI's risk_tier vocabulary)
    explanation: str
    key_factors: List[str] = field(default_factory=list)
    model_used: str = ""
    discovery_mode: str = ""      # "sdk-auto-discovered", "static-env-fallback", or "openai-fallback"
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


def _openai_fallback_completion(messages: list) -> str:
    """Sends the same chat messages to OpenAI's API when Foundry Local is
    unavailable or fails to run the model. Returns raw text in the same
    format `parse_response()` already expects from Foundry.

    Raises:
        LLMRiskAssessmentError: if the OpenAI call itself fails (e.g. no
            API key configured, network error, rate limit, or timeout).
    """
    try:
        from openai import OpenAI
    except ImportError as e:
        raise LLMRiskAssessmentError(
            "openai package is not installed; cannot use fallback."
        ) from e

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMRiskAssessmentError(
            "OPENAI_API_KEY is not set; cannot use OpenAI fallback."
        )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=OPENAI_FALLBACK_MODEL,
            messages=messages,
            timeout=OPENAI_FALLBACK_TIMEOUT_SECONDS,  # don't let a hung call block the registration endpoint
        )
        return response.choices[0].message.content
    except Exception as e:
        raise LLMRiskAssessmentError(f"OpenAI fallback call failed: {e}") from e


def suggest_risk_tier(
    system_description: str,
    *,
    preprocessors: Optional[List[TextPreprocessor]] = None,
    client: Optional[FoundryClient] = None,
) -> RiskSuggestion:
    """Suggests an EU AI Act risk tier for a plain-language AI system
    description, using the configured local LLM via Foundry Local.

    Falls back to OpenAI automatically if Foundry Local cannot be reached
    or fails to run the model (e.g. Out-Of-Memory on the local machine).

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
        contributing factors the model identified. Callers should check
        `discovery_mode == "openai-fallback"` if they want to record that
        this particular suggestion came from the cloud fallback rather
        than the local model (e.g. for an audit log entry).

    Raises:
        ValueError: if `system_description` is empty/blank.
        LLMRiskAssessmentError: if both Foundry Local and the OpenAI
            fallback fail.
        LLMResponseParseError: the model's response couldn't be parsed into
            a valid structured suggestion.
    """
    if not system_description or not system_description.strip():
        raise ValueError("system_description must be a non-empty string.")

    text = run_pipeline(system_description, preprocessors)
    messages = build_messages(text)

    try:
        active_client = client or get_default_client()
        raw_response = active_client.chat_completion(messages)
        model_used = active_client.model_id
        discovery_mode = active_client.connection_info.discovery_mode
    except (FoundryConnectionError, FoundryModelError):
        # Foundry Local is unreachable or failed to run the model
        # (e.g. OOM) — fall back to OpenAI so registration doesn't fail.
        raw_response = _openai_fallback_completion(messages)
        model_used = OPENAI_FALLBACK_MODEL
        discovery_mode = "openai-fallback"

    parsed = parse_response(raw_response)

    return RiskSuggestion(
        eu_ai_act_label=parsed["eu_ai_act_label"],
        internal_tier=parsed["internal_tier"],
        explanation=parsed["explanation"],
        key_factors=parsed["key_factors"],
        model_used=model_used,
        discovery_mode=discovery_mode,
        raw_response=raw_response,
        masked_text=text,
    )