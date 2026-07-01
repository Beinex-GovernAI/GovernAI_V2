"""Typed exceptions for the LLM-powered Risk Tier Suggestion feature.

Kept separate from `foundry_client.py` so the Streamlit UI layer can
`except` on them without importing the client internals.
"""


class LLMRiskAssessmentError(Exception):
    """Base class for all errors raised by the LLM risk-suggestion pipeline."""


class FoundryConnectionError(LLMRiskAssessmentError):
    """Raised when Foundry Local's local service cannot be reached at all.

    Typically means: the Foundry Local service isn't running, or the
    configured/auto-discovered base URL is stale or unreachable.
    """


class FoundryModelError(LLMRiskAssessmentError):
    """Raised when the service is reachable but the model itself failed.

    Covers: the requested model alias isn't downloaded/loaded, the model
    failed to load, or the inference call itself returned an error.
    """


class LLMResponseParseError(LLMRiskAssessmentError):
    """Raised when the model responded, but its output could not be parsed
    into a valid structured risk-tier suggestion (e.g. malformed JSON, or
    a tier value outside the EU AI Act vocabulary)."""
