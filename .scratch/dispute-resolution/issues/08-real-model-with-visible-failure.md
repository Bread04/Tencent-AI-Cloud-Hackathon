# 08: Run on the real model with visible failure

**What to build:** The system runs on a real model through the adapter, using an OpenAI-compatible endpoint from the confirmed provider. Credentials come from the environment and are never committed. Every model call has a timeout. Output that fails validation is retried with the error fed back, up to the repair budget. If the model is unreachable or keeps failing, the run stops with a clear error and the Case goes to review, never to a made-up Ruling. Switching between the stub and the real model is one setting.

**Blocked by:** 02

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Kyven

- [ ] The provider and model are confirmed and recorded, including whether it accepts images
- [ ] One setting switches between the stub and the real model
- [ ] Credentials are read from the environment and are absent from the repo
- [ ] Structured output is requested and validated against the contract
- [ ] A timed-out call is treated as a failure, not a hang
- [ ] Invalid output is retried with the validation error, up to two times
- [ ] With the model unreachable, the user sees a clear error and the Case is marked for review
- [ ] One mock case resolves end to end on the real model
