"""
Low-level client for talking to a model served locally through
**Azure AI Foundry Local** (an OpenAI-compatible local inference server).

Why this exists (the "moving endpoint" problem)
-------------------------------------------------
Foundry Local's web service binds to a port chosen at runtime, and that
port can change every time `foundry service start` runs again or the
machine reboots. Hard-coding a base URL in `.env` would mean editing the
file by hand after every restart.

To avoid that, this client *prefers* the official `foundry-local-sdk`
package (`from foundry_local import FoundryLocalManager`). Constructing
`FoundryLocalManager(alias)`:
  1. Starts the Foundry Local service if it isn't already running.
  2. Downloads/loads the requested model alias if needed.
  3. Exposes `.endpoint` and `.api_key`, which always reflect the
     *current* live address -- no manual port-chasing required.

If the SDK isn't installed, or it can't reach/bootstrap the local
service for any reason, the client falls back to a statically configured
`FOUNDRY_BASE_URL` from `.env`. This keeps the app usable even without the
SDK, at the cost of needing a manual update if the port ever changes --
see `setup.md` / `LLM_RISK_SUGGESTION.md` for that fallback workflow.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

from .exceptions import FoundryConnectionError, FoundryModelError

load_dotenv()

DEFAULT_MODEL_ALIAS = os.environ.get("FOUNDRY_MODEL_ALIAS", "phi-3.5-mini")
DEFAULT_FALLBACK_BASE_URL = os.environ.get("FOUNDRY_BASE_URL", "http://127.0.0.1:62181/v1")
DEFAULT_API_KEY = os.environ.get("FOUNDRY_API_KEY", "not-required-for-local-use")
DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("FOUNDRY_TIMEOUT_SECONDS", "60"))
DEFAULT_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "600"))
DEFAULT_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.1"))


@dataclass
class ConnectionInfo:
    base_url: str
    api_key: str
    model_id: str
    discovery_mode: str  # "sdk-auto-discovered" or "static-env-fallback"


class FoundryClient:
    """Modular wrapper around the Foundry Local OpenAI-compatible API.

    Usage:
        client = FoundryClient()              # uses FOUNDRY_MODEL_ALIAS from .env
        reply = client.chat_completion(messages)

    The client connects lazily on first use (not at import time), and
    caches the connection for the lifetime of the instance.
    """

    def __init__(self, model_alias: Optional[str] = None):
        self.model_alias = model_alias or DEFAULT_MODEL_ALIAS
        self._openai_client = None
        self._connection_info: Optional[ConnectionInfo] = None

    # -- connection -------------------------------------------------------

    def _connect(self) -> ConnectionInfo:
        """Resolves the live Foundry Local endpoint, preferring SDK
        auto-discovery and falling back to static `.env` configuration."""
        try:
            from foundry_local import FoundryLocalManager  # type: ignore

            manager = FoundryLocalManager(self.model_alias)
            model_info = manager.get_model_info(self.model_alias)
            return ConnectionInfo(
                base_url=manager.endpoint,
                api_key=manager.api_key,
                model_id=model_info.id,
                discovery_mode="sdk-auto-discovered",
            )
        except ImportError:
            # foundry-local-sdk not installed -- fall back silently.
            pass
        except Exception as exc:
            # SDK is installed but couldn't reach/bootstrap the service
            # (not running, model not downloaded, etc). Fall back to the
            # static .env endpoint rather than failing outright, since the
            # person may be pointing at a manually-configured endpoint.
            self._last_sdk_error = exc

        # Fallback: static configuration from .env
        return ConnectionInfo(
            base_url=DEFAULT_FALLBACK_BASE_URL,
            api_key=DEFAULT_API_KEY,
            model_id=self.model_alias,
            discovery_mode="static-env-fallback",
        )

    def _ensure_client(self):
        if self._openai_client is not None:
            return

        import openai

        self._connection_info = self._connect()
        self._openai_client = openai.OpenAI(
            base_url=self._connection_info.base_url,
            api_key=self._connection_info.api_key,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )

    @property
    def connection_info(self) -> ConnectionInfo:
        self._ensure_client()
        return self._connection_info

    @property
    def model_id(self) -> str:
        return self.connection_info.model_id

    # -- inference ----------------------------------------------------------

    def chat_completion(
        self,
        messages: list[dict],
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        """Sends a chat completion request and returns the raw text content.

        Raises:
            FoundryConnectionError: the local service could not be reached.
            FoundryModelError: the service responded but the model/inference
                call itself failed (model not loaded, bad request, etc).
        """
        self._ensure_client()

        import openai

        try:
            response = self._openai_client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except openai.APIConnectionError as exc:
            raise FoundryConnectionError(
                "Could not reach Foundry Local at "
                f"'{self._connection_info.base_url}'. Make sure the service is "
                "running (`foundry service start`) and the model is loaded "
                f"(`foundry model run {self.model_alias}`)."
            ) from exc
        except openai.APITimeoutError as exc:
            raise FoundryConnectionError(
                "Foundry Local did not respond in time. The model may still "
                "be loading -- try again in a few seconds, or check "
                "`foundry service status`."
            ) from exc
        except openai.NotFoundError as exc:
            raise FoundryModelError(
                f"Model '{self.model_id}' was not found by Foundry Local. "
                f"Run `foundry model run {self.model_alias}` to download/load it."
            ) from exc
        except openai.APIStatusError as exc:
            raise FoundryModelError(
                f"Foundry Local returned an error (status {exc.status_code}): "
                f"{exc.message}"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - surface anything unexpected
            raise FoundryModelError(f"Unexpected error calling Foundry Local: {exc}") from exc

        if not response.choices:
            raise FoundryModelError("Foundry Local returned an empty response (no choices).")

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise FoundryModelError("Foundry Local returned an empty completion.")

        return content


_default_client: Optional[FoundryClient] = None


def get_default_client() -> FoundryClient:
    """Returns a process-wide cached FoundryClient using the configured
    default model alias. Streamlit reruns the script on every interaction,
    so caching here avoids reconnecting/re-discovering the endpoint on
    every keystroke."""
    global _default_client
    if _default_client is None:
        _default_client = FoundryClient()
    return _default_client
