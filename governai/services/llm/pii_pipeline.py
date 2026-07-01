"""Pre-processing pipeline extension point for the LLM risk-suggestion flow.

Today this is a no-op: `DEFAULT_PREPROCESSORS` is empty, so the plain-language
description typed into Risk Setup goes to the local model unmodified.

Future work (not implemented yet)
------------------------------------
A PII detection/masking step using the **Kiji Privacy Proxy** (running on
WSL) is planned, with this intended flow:

    User Input -> Kiji Privacy Proxy (PII masking) -> LLM Risk Assessment -> Response

`risk_suggester.suggest_risk_tier()` runs every callable in its
`preprocessors` argument (which defaults to `DEFAULT_PREPROCESSORS`, below)
over the description text, in order, before it's sent to the model. That
means wiring in Kiji later should only require changes in *this file* --
no changes to `risk_suggester.py`, `foundry_client.py`, or the Streamlit
page should be necessary.

Sketch of what that addition will look like once Kiji is ready:

    import requests

    KIJI_PROXY_URL = os.environ.get("KIJI_PROXY_URL", "http://localhost:8089/mask")

    def mask_pii_with_kiji(text: str) -> str:
        \"\"\"Sends text through the local Kiji Privacy Proxy and returns the
        PII-masked version.\"\"\"
        response = requests.post(KIJI_PROXY_URL, json={"text": text}, timeout=10)
        response.raise_for_status()
        return response.json()["masked_text"]

    DEFAULT_PREPROCESSORS: List[TextPreprocessor] = [mask_pii_with_kiji]

Until then, `DEFAULT_PREPROCESSORS` stays empty on purpose -- per the current
scope, the Kiji proxy itself is intentionally not implemented here.
"""

from __future__ import annotations

from typing import Callable, List

# A preprocessor takes the raw description text and returns a (possibly
# transformed) version of it. Each one runs in order before the LLM call.
TextPreprocessor = Callable[[str], str]

DEFAULT_PREPROCESSORS: List[TextPreprocessor] = []


def run_pipeline(text: str, preprocessors: List[TextPreprocessor] | None = None) -> str:
    """Runs `text` through each preprocessor in order and returns the result."""
    for step in (preprocessors if preprocessors is not None else DEFAULT_PREPROCESSORS):
        text = step(text)
    return text
