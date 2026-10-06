# Dev Guide: how we build this with two people and no merge conflicts

Deadline: **Thu 15 Oct 2026**. Weekdays are busy, so the real build window is **Fri 9 Oct to Sun 11 Oct**, then short evenings. Vocabulary is defined in [GLOSSARY.md](../GLOSSARY.md); the intended flow is in [workflow.md](../workflow.md).

## Commitment

Three core agents (Rider Advocate, Driver Advocate, Judge) resolving **Route Deviation** and **No-Show** cases, on mock data and mock policy, with a visible agent log and a simple web UI. Escalation only if there is slack. Policy & Precedent, Property Damage, Image Analysis, Fraud: not planned.

## Stack (assumed, change by mutual agreement)

- Python 3.11, `pydantic` for the Case contract, `FastAPI` for the backend, plain HTML/JS for the UI.
- LLM behind one function `llm.complete(messages) -> str`. Hunyuan through its OpenAI-compatible API; a stub implementation for offline work.
- Agents are plain Python classes that call the LLM and tools. No agent framework.

## Ownership (the rule that prevents conflicts)

Each person edits only their own folders. Anything in the shared zone changes through the other person's approval.

The work is split along the pipeline, not by layer: **Kyven builds the cases, Braedon rules on them and shows the result.** The handoff point is the `Submission`.

| Zone | Owner | Contents |
| --- | --- | --- |
| `src/contracts.py` | **Shared** | Case, EvidenceItem, Submission, Ruling, LogEvent, tool signatures |
| `src/llm/`, `src/tools/evidence/`, `src/agents/advocates/`, `src/orchestrator/`, `data/cases/` | **Kyven** (case building) | LLM adapter and stub, evidence tools (GPS, chat, fare, history), Rider Advocate, Driver Advocate, the run loop and log emission, mock cases |
| `src/tools/policy/`, `src/agents/judge/`, `src/api/`, `web/`, `data/policy/`, `docs/` | **Braedon** (ruling and presentation) | Policy text and policy tool, Judge (including the per-argument rebuttal), API endpoints, web UI and live log view, architecture diagram, demo script |

**Why this split balances.** Kyven's heaviest piece is the mock data and evidence analysis (route distance, wait times); Braedon's heaviest pieces are the Judge prompt and the UI. Each side has roughly one hard agent-shaped job, one data or tool job and some small glue.

### How you work without waiting on each other

- **Fixtures are the decoupling.** Kyven commits two hand-written sample Submissions per category to `fixtures/submissions/` on Wed; Braedon builds and tests the Judge against those and never needs Kyven's advocates to run.
- **Braedon commits a policy stub on Thu** (clause IDs and a few lines each) so Kyven's advocates have something to cite. The real wording can replace it later without changing IDs.
- **Kyven commits a sample LogEvent stream** to `fixtures/logs/` so Braedon can build the log view before the orchestrator exists.
- The orchestrator is Kyven's. It calls Braedon's Judge through one function: `judge(case, rider_submission, driver_submission) -> Ruling`.

## Day 0 (30 to 60 minutes, together): freeze the contract

1. Sketch `contracts.py` together. Decide at this point:
   - **Ruling** fields: outcome (`uphold` / `partial` / `reject` of the claimant's claim), amount and currency, confidence (0 to 1), reasoning, cited evidence IDs, cited clause IDs, per-argument rebuttal.
   - **EvidenceItem**: `id`, `source`, `trip_id`, `timestamp`, `status` (`available` / `missing`), `content`.
   - **LogEvent**: `case_id`, `timestamp`, `agent`, `kind` (`evidence_request`, `evidence_response`, `submission`, `ruling`), `summary`. The log shows decisions and citations, not private model reasoning.
   - **Tool signatures**, for example `get_gps(trip_id)`, `get_chat(trip_id)`, `get_fare(trip_id)`, `get_history(party_id)`, `get_policy(category)`.
2. One person commits it. After that, edits to the contract are a PR the other approves.

## Branching

- `main` stays runnable. Work on `kyven/<topic>` and `braedon/<topic>` branches, merge small and often (at least once per session).
- Rebase on `main` before merging. Never edit the other person's folders; ask for the change instead.

## Timeline

| When | Kyven | Braedon |
| --- | --- | --- |
| Wed 7 Oct (evening) | Day 0 contract together | Day 0 contract together |
| Thu 8 Oct | LLM adapter and stub; sample Submission and LogEvent fixtures; start mock cases | Policy stub with clause IDs (resolve the 5-minute vs 8-minute wait ambiguity); Judge skeleton returning a canned Ruling |
| Fri 9 Oct | Mock data for 2 to 3 No-Show and 2 to 3 Route Deviation cases, including one the rider should win; fix the DISP-002 speed and timeline issues in a **copy**; evidence tools | Real policy wording and policy tool; Judge prompt developed against the fixtures |
| Sat 10 Oct | Rider and Driver Advocates with real prompts; orchestrator emitting log events | `/cases` and `/run` endpoints; web UI shell; live log view built on the fixture stream |
| Sun 11 Oct | **Integration day, together:** wire advocates to the Judge, switch to the real LLM, make both categories resolve end to end | Same; Ruling card with each party's Outcome |
| Mon 12 Oct | Prompt tuning for the advocates; Escalation if there is slack | Judge tuning (rebuttal quality, confidence); architecture diagram; demo script |
| Tue 13 Oct | **Feature freeze.** Bug fixes only | Rehearse the demo end to end, twice |
| Wed 14 Oct | Buffer and submission prep | Buffer and submission prep |
| Thu 15 Oct | **Deadline** | |

## Rules for the data

- Strip `Expected ruling` and the Evidence Summary from any case file before the agents see it. Keep them as an evaluation label in a separate field.
- Missing evidence stays marked `missing`. Agents must not invent records.
- History is context for the Judge. It never decides a ruling by itself.
- Label every mock case, policy and financial action as simulated on screen.

## Definition of done (before Tue 13 Oct)

- [ ] The three agents run end to end for Route Deviation and No-Show.
- [ ] The log shows evidence requests and responses, both Submissions, and the Ruling.
- [ ] The Ruling shows outcome, amount, confidence, reasoning, cited evidence and clauses.
- [ ] Both parties see their own Outcome.
- [ ] One case is ruled for the rider and one for the driver.
- [ ] The architecture diagram and demo script exist.
- [ ] Simulated data and policy are labelled as such.

## First three actions

1. Both of you read this file and [workflow.md](../workflow.md), and agree a time for the Day 0 contract session.
2. Kyven creates the repo skeleton (`src/`, `data/`, `web/`, `requirements.txt`) and the LLM stub, then commits the sample Submission fixtures.
3. Braedon starts the policy stub, because the advocates can't cite anything without clause IDs.
