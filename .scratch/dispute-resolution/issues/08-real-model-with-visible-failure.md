# 08: Run on the real model with visible failure

**What to build:** The system runs on a real model through the adapter, using an OpenAI-compatible endpoint from the confirmed provider. Credentials come from the environment and are never committed. Every model call has a timeout. Output that fails validation is retried with the error fed back, up to the repair budget. If the model is unreachable or keeps failing, the run stops with a clear error and the Case goes to review, never to a made-up Ruling. Switching between the stub and the real model is one setting.

**Blocked by:** 02

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Kyven

- [ ] The provider and model are confirmed and recorded, including whether it accepts images
- [x] One setting switches between the stub and the real model (`MODEL_PROVIDER=stub|openai_compatible`, `src/llm/factory.py`)
- [x] Credentials are read from the environment and are absent from the repo (`MODEL_BASE_URL`, `MODEL_API_KEY`, `MODEL_NAME`; names only in `.env.example`; the key is never in the repr or an error message)
- [x] Structured output is requested and validated against the contract (`response_format` json_schema, then `model_validate_json`; `src/llm/client.py`)
- [x] A timed-out call is treated as a failure, not a hang (`MODEL_TIMEOUT_SECONDS`, default 30)
- [x] Invalid output is retried with the validation error, up to two times, using the shared repair helper from ticket 04 (the advocates and the Judge already use `complete_with_repair`; the client raises `ValidationError` for it)
- [x] With the model unreachable, the user sees a clear error and the Case is marked for review (checked on a real HTTP timeout with `scripts/try_model.py`)
- [ ] One mock case resolves end to end on the real model

**Still open:** confirm the provider and model (and whether it accepts images), then run one mock case on it:
`MODEL_PROVIDER=openai_compatible MODEL_BASE_URL=... MODEL_API_KEY=... MODEL_NAME=... uv run python -m scripts.try_model DISP-003`.
Until a real key has been used, the client has only been tested against a fake HTTP server.
