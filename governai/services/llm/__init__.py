"""
LLM-powered Risk Tier Suggestion module.

Public entry point: `suggest_risk_tier()` from `risk_suggester`.

Package layout
--------------
- foundry_client.py    Low-level wrapper around Azure AI Foundry Local
                        (OpenAI-compatible local inference server).
- prompt_templates.py  Prompt construction + structured-response parsing.
- pii_pipeline.py      Extension point for the future Kiji Privacy Proxy
                        PII-masking step (currently a no-op).
- risk_suggester.py    High-level orchestration used by the Streamlit UI.
- exceptions.py        Typed exceptions surfaced to the UI layer.
"""

from .risk_suggester import RiskSuggestion, suggest_risk_tier
from .exceptions import (
    LLMRiskAssessmentError,
    FoundryConnectionError,
    FoundryModelError,
    LLMResponseParseError,
)

__all__ = [
    "RiskSuggestion",
    "suggest_risk_tier",
    "LLMRiskAssessmentError",
    "FoundryConnectionError",
    "FoundryModelError",
    "LLMResponseParseError",
]
