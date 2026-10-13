# 08: Run on the real model with visible failure

**What to build:** The system runs on a real model through the adapter, using an OpenAI-compatible endpoint from the confirmed provider. Credentials come from the environment and are never committed. Every model call has a timeout. Output that fails validation is retried with the error fed back, up to the repair budget. If the model is unreachable or keeps failing, the run stops with a clear error and the Case goes to review, never to a made-up Ruling. Switching between the stub and the real model is one setting.

**Blocked by:** 02

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Kyven

- [x] The provider and model are confirmed and recorded, including whether it accepts images (Google Gemini via its OpenAI-compatible endpoint, model `gemini-3.5-flash-lite`)
- [x] One setting switches between the stub and the real model (`MODEL_PROVIDER=stub|openai_compatible`, `src/llm/factory.py`)
- [x] Credentials are read from the environment and are absent from the repo (`MODEL_BASE_URL`, `MODEL_API_KEY`, `MODEL_NAME`; names only in `.env.example`; the key is never in the repr or an error message)
- [x] Structured output is requested and validated against the contract (`response_format` json_schema, then `model_validate_json`; `src/llm/client.py`)
- [x] A timed-out call is treated as a failure, not a hang (`MODEL_TIMEOUT_SECONDS`, default 30)
- [x] Invalid output is retried with the validation error, up to two times, using the shared repair helper from ticket 04 (the advocates and the Judge already use `complete_with_repair`; the client raises `ValidationError` for it)
- [x] With the model unreachable, the user sees a clear error and the Case is marked for review (checked on a real HTTP timeout with `scripts/try_model.py`)
- [x] One mock case resolves end to end on the real model (DISP-003 on OpenRouter free models: `apodex/apodex-1.1-mini:free` gave uphold, fee_reversal, SGD 5.00, Confidence 0.80; `nvidia/nemotron-3-super-120b-a12b:free` gave the same at 0.75)

**Dev provider (not the final choice):** OpenRouter's free models, an OpenAI-compatible gateway. Use
`MODEL_BASE_URL=https://openrouter.ai/api/v1`, `MODEL_STRUCTURED_OUTPUT=json_object` (the Apodex provider rejects a JSON schema) and a longer
`MODEL_TIMEOUT_SECONDS` (free models are slow). Free models are rate-limited (HTTP 429), which the system reports as a held Case.
Models seen: Apodex 1.1 mini and Nemotron 3 Super (text only); Gemma 4, Dots 3 note and Inkling accept images but were not tried.

**Real-model results so far** (Apodex 1.1 mini, plain JSON mode):
- DISP-003: resolved and matches its label.
- DISP-002: held for review. The Judge cited the missing rider-location item as fact, and code refused it after the repair attempts.
- DISP-004: held for review. The Judge's reply did not match the required format.
Those two show the safety path working, not a made-up Ruling. A stronger model is needed for the other cases.

**Confirmed provider (13 Oct 2026):** Google Gemini via its OpenAI-compatible endpoint.
`MODEL_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`, `MODEL_NAME=gemini-3.5-flash-lite`,
`MODEL_TIMEOUT_SECONDS=300`, `MODEL_RATE_LIMIT_RETRIES=8` (recorded in `.env`, git-ignored). The endpoint is
OpenAI-compatible, so `MODEL_PROVIDER=openai_compatible` is unchanged. Tier 3 image support is satisfied by Gemini's
vision-capable models; confirm the specific `gemini-3.5-flash-lite` vision behaviour when a photo case first runs on the real model.

Known gap: the timeout is per phase (connect, read, write), not a wall-clock cap, and one dispute can make about seven calls with no overall budget.
