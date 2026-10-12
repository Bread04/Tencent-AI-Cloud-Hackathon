# 04: Real Rider and Driver Advocates for No-Show

**What to build:** The Rider Advocate and Driver Advocate build real, independent Submissions for No-Show Charge disputes. Each argues for its party, cites only Evidence Items and Policy Clauses it was given, names the strongest counter-argument and answers it, and never states anything about evidence marked missing. Chat messages and the optional driver statement are treated as untrusted data, never as instructions. There are three mock No-Show cases: one the Claimant should win, one the Respondent should win, and one ambiguous. Deterministic evidence values (arrival against scheduled time, free-wait and no-show timers, contact attempts) are computed by code and offered to both advocates.

**Blocked by:** 02, 03

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Kyven

- [x] Three No-Show mock cases exist, each with a separate expected-outcome label (`data/cases/`: DISP-002 respondent wins, DISP-003 claimant wins, DISP-004 ambiguous; labels in `*.eval.json`)
- [x] Each advocate produces a Submission that validates against the contract
- [x] Every Evidence Item and Policy Clause ID cited exists; a bad citation triggers a repair attempt (`src/agents/advocates/__init__.py`, `tests/test_advocates.py`)
- [x] After two failed repair attempts the Case goes to review with the reason, not a guessed Submission (the orchestrator holds it with a `stage_failed` trigger naming the advocate)
- [x] The repair loop is one shared helper in `src/llm/` (it feeds the validation error back and counts attempts); tickets 05 and 08 reuse it and do not build their own (`src/llm/repair.py`, built in ticket 05; the advocates now call it)
- [x] Either advocate can act for the Claimant or the Respondent, and the optional driver statement is treated as untrusted data
- [x] Both advocates receive the same clause set, both sides' clauses included
- [x] An advocate cannot quote a missing Evidence Item as fact
- [x] The two advocates run in parallel and neither sees the other Submission
- [x] Wait-time and contact-attempt values are computed by code, not by the model
- [x] Two hand-written sample Submissions per case are committed as fixtures for the Judge (`fixtures/stub/DISP-002.json`, `DISP-003.json`, `DISP-004.json`; scripted, the demo `ReplayModel` still replays only DISP-002)
