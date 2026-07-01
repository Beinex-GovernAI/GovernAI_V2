# LLM-Powered Risk Tier Suggestion -- Setup & Notes

This document covers the new feature only. For the rest of the app, see
`README.md` and `setup.md`.

## What was built

A modular LLM-assisted assistant, surfaced as an "🤖 AI-Assisted Tier
Suggestion (Beta)" panel on the **Risk Setup** page. You type a
plain-language description of an AI system and get back:
- A suggested EU AI Act tier (`Unacceptable Risk` / `High Risk` /
  `Limited Risk` / `Minimal Risk`), shown alongside GovernAI's internal
  tier vocabulary (`Prohibited` / `High` / `Limited` / `Minimal`).
- A short explanation.
- The specific factors in the description that drove the classification.

It's advisory only: nothing is written to the database from this panel
except an audit log entry (`LLM_RISK_SUGGESTION`) recording that a
suggestion was generated, for traceability. The actual risk tier assigned
to a system still only changes through the existing questionnaire
(`risk_svc.assess_risk`) below it on the same page.

## New files

```text
governai/services/llm/
├── __init__.py            # public API: suggest_risk_tier(), RiskSuggestion, exceptions
├── foundry_client.py       # talks to Foundry Local's OpenAI-compatible API
├── prompt_templates.py     # builds the prompt; parses/validates the JSON response
├── pii_pipeline.py         # no-op today; extension point for Kiji (see below)
├── risk_suggester.py       # orchestrates pipeline -> prompt -> client -> parse
└── exceptions.py           # FoundryConnectionError / FoundryModelError / LLMResponseParseError
```

`governai/pages/3_Risk_Setup.py` was updated to import and call
`suggest_risk_tier()` from `services.llm`; no other existing files changed.

## Configuration (`.env`)

Copy `.env.example` to `.env` at the project root and adjust as needed:

| Variable | Default | Purpose |
|---|---|---|
| `FOUNDRY_MODEL_ALIAS` | `qwen3.5-2b` | Model to load via Foundry Local. Change this one line to swap models. |
| `FOUNDRY_BASE_URL` | `http://localhost:5273/v1` | **Fallback only** -- used if endpoint auto-discovery fails (see below). |
| `FOUNDRY_API_KEY` | `not-required-for-local-use` | Not required for local-only Foundry Local usage. |
| `FOUNDRY_TIMEOUT_SECONDS` | `60` | Per-request timeout. |
| `LLM_MAX_TOKENS` | `600` | Generation cap. |
| `LLM_TEMPERATURE` | `0.1` | Kept low/deterministic for a classification task. |

## The "moving endpoint" problem -- and how it's handled

Foundry Local's web service binds to a port chosen at runtime, and that
port is not guaranteed to stay the same across restarts. To avoid needing
to manually update `FOUNDRY_BASE_URL` every time `foundry service start`
runs:

`foundry_client.py` uses the official **`foundry-local-sdk`** package
(`from foundry_local import FoundryLocalManager`). Constructing
`FoundryLocalManager(FOUNDRY_MODEL_ALIAS)`:
1. Starts the Foundry Local service if it isn't already running.
2. Loads the model alias if it isn't already loaded.
3. Exposes `.endpoint` / `.api_key`, which always reflect the **current**
   live address.

This means in the common case, **you do not need to set or update
`FOUNDRY_BASE_URL` at all** -- it's only used as a fallback if:
- `foundry-local-sdk` isn't installed, or
- the SDK is installed but can't reach/bootstrap the service for some
  other reason (e.g. Foundry Local isn't installed on this machine, or
  the native runtime failed to start).

In that fallback case, run `foundry service status` to get the current
URL and paste it into `FOUNDRY_BASE_URL` in `.env`.

### Why `foundry-local-sdk` is pinned to `0.5.1`

As of this writing, the `foundry-local-sdk` PyPI package jumped from a
lightweight `0.x` line (a thin REST client, module name `foundry_local`)
to a `1.x` line (module name `foundry_local_sdk`) that's a full rewrite
using native ctypes bindings and pulls in CUDA/GPU-targeted dependencies.
That's unnecessary complexity and weight for this CPU-friendly, single
local-model use case, so `requirements.txt` pins to `0.5.1`, the last
release of the simple client. If you intentionally want the new native
SDK later, you'll need to rewrite `foundry_client._connect()` against its
very different API (`FoundryLocalManager.initialize(config)` + catalog
objects instead of `FoundryLocalManager(alias).endpoint`).

## Error handling

`foundry_client.py` translates failures into three typed exceptions
(caught and shown as a friendly `st.error(...)` in the Streamlit UI):

- **`FoundryConnectionError`** -- the local service couldn't be reached at
  all (not running, stale endpoint, timeout).
- **`FoundryModelError`** -- the service responded, but the model itself
  wasn't loaded, or inference failed.
- **`LLMResponseParseError`** -- the model replied, but its output wasn't
  valid/parseable JSON, or named a tier outside the EU AI Act vocabulary.
  (Small local models occasionally wrap JSON in prose or markdown fences
  despite instructions not to -- `prompt_templates._extract_json_object()`
  tries a couple of recovery strategies before giving up.)

## Future work: Kiji Privacy Proxy (not implemented)

Per the current scope, **PII masking via the Kiji Privacy Proxy is not
implemented yet**. The module is structured so it can be added without
touching `risk_suggester.py`, `foundry_client.py`, or the Streamlit page:

`risk_suggester.suggest_risk_tier()` already runs the description through
a list of `preprocessors` (default: `pii_pipeline.DEFAULT_PREPROCESSORS`,
currently empty) before sending anything to the model. To wire in Kiji
later:

1. Add a function to `pii_pipeline.py` that calls the local Kiji proxy
   (sketch included as a comment in that file).
2. Add it to `DEFAULT_PREPROCESSORS`.

No other file needs to change for the
`User Input -> Kiji Privacy Proxy -> LLM Risk Assessment -> Response`
flow described in the task to start working.

## Known limitations

- Small local models (2B-class) can occasionally produce a tier
  inconsistent with their own stated reasoning, or omit `key_factors`.
  The parser is lenient about formatting but does not attempt to
  second-guess the model's classification itself.
- This feature is advisory and intentionally does not write to
  `risk_assessments` / `AISystem.risk_tier` -- only the formal
  questionnaire (`risk_svc.assess_risk`) does that, to keep a single
  source of truth for the recorded risk tier.
- No retry/backoff is implemented for transient Foundry Local errors;
  the user can just click "Suggest Risk Tier" again.
