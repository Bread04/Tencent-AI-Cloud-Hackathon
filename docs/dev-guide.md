# Dev Guide: how we build this with two people and no merge conflicts

Deadline: **Thu 15 Oct 2026**. Weekdays are busy, so the real build window is **Fri 9 Oct to Sun 11 Oct**, then short evenings. Vocabulary is in [GLOSSARY.md](../GLOSSARY.md), the flow in [workflow.md](../workflow.md), behaviour in [spec.md](spec.md), and the agent design in [architecture.md](architecture.md).

## Commitment

Every agent in `workflow.md` except the Fraud and Bad-Faith Detection Agent, across all four Dispute Categories, on mock data and mock policy, with a visible Communication Log and a web UI. It is built in **tiers**: each tier must work end to end before the next starts, and if time runs out we stop at a tier boundary.

| Tier | Contents | Target |
| --- | --- | --- |
| **0, required MVP** | Rider Advocate, Driver Advocate, Judge on Route Deviation and No-Show Charge; Communication Log; web UI | Sat 10 Oct night |
| **1** | Escalation Protocol, Policy & Precedent, Rider and Driver Evidence Agents | Sun 11 Oct |
| **2** | SLA & Routing Manager, Safety Incident category | Mon 12 Oct |
| **3** | Image Analysis with Authenticity checks, Property Damage category | Tue 13 Oct |
| **4** | Learning Feedback Loop | Only if ahead of schedule |

**Go or no-go rule.** At each target, if the tier is not working end to end, do not start the next one. Finish it, and drop the lowest tier instead. Tier 0 is the graded deliverable; nothing above it is worth a broken demo.

## Stack (assumed, change by mutual agreement)

- Python 3.11, `pydantic` for the contract, `FastAPI` for the backend, plain HTML/JS for the UI.
- One model adapter with an offline stub and a client for an OpenAI-compatible endpoint. Provider to be confirmed; Tier 3 needs a model that accepts images.
- Agents are plain Python classes. No agent framework.

## Ownership (the rule that prevents conflicts)

Each person edits only their own folders. Anything shared changes through the other person's approval.

The split follows the pipeline: **Kyven builds the cases, Braedon rules on them and shows the result.** The main handoff is the `Submission`.

| Zone | Owner | Contents |
| --- | --- | --- |
| `src/contracts.py`, `src/config.py` | **Shared** (Braedon holds the pen on config) | Contract objects, tool signatures, the on/off switches for each supporting agent |
| `src/llm/`, `src/store/`, `src/orchestrator/` | **Kyven** | Model adapter and stub, Case store, the stage-by-stage run loop, log emission |
| `src/tools/evidence/`, `src/agents/evidence/`, `src/agents/image/` | **Kyven** | Evidence tools (GPS, chat, fare, history), Rider and Driver Evidence Agents, Image Analysis and Authenticity |
| `src/agents/advocates/`, `src/intake/` | **Kyven** | Rider Advocate, Driver Advocate, intake validation |
| `data/cases/`, `fixtures/submissions/`, `fixtures/logs/` | **Kyven** | Mock cases with separate evaluation labels, sample Submissions, sample log stream |
| `src/agents/policy/`, `data/policy/`, `data/precedent/` | **Braedon** | Policy text, Policy & Precedent store and agent |
| `src/agents/judge/` | **Braedon** | Judge, self-check pass, stability check, Confidence |
| `src/agents/escalation/`, `src/agents/sla/`, `src/agents/learning/` | **Braedon** | Escalation Protocol, review queue, SLA & Routing Manager, Learning Feedback Loop |
| `src/api/`, `web/`, `docs/` | **Braedon** | API endpoints, web UI and log view, reviewer screen, architecture diagram, demo script |

**Balance.** Kyven carries the evidence and data work plus the two advocates and, late, Image Analysis. Braedon carries the Judge and the review path plus the UI. Each has one hard model-shaped job in Tier 0 and roughly two supporting agents after it.

### How you work without waiting on each other

- **Fixtures are the decoupling.** Kyven commits two hand-written sample Submissions per category and a sample log stream early; Braedon builds the Judge and the log view against those without needing the advocates or the orchestrator to run.
- **Braedon commits a policy stub on Thu** (clause IDs and a few lines each) so Kyven's advocates have something to cite. Wording can change later without changing IDs.
- **Every supporting agent sits behind a switch.** A switched-off agent is skipped, so an unfinished agent on one side never blocks the other.
- **Calls between the halves**, all fixed in the contract: the Judge (`judge(case, rider_submission, driver_submission) -> Ruling`), policy and precedent lookup, and the escalation check the orchestrator calls after a Ruling.

## Day 0 (30 to 60 minutes, together): freeze the contract

Work through section 12 of [architecture.md](architecture.md):

1. Fields and types of each contract object: Dispute, Case, Evidence Item, Submission, Policy Clause, Precedent, Ruling, Outcome, Log event.
2. Confidence components, caps and the default escalation threshold (proposed: 0.7).
3. The list of escalation triggers.
4. Structured-output format and the model provider, including a vision-capable model for Tier 3.
5. Tool signatures and the switch names.
6. Mock policy wording, including the free-wait versus no-show threshold ambiguity.

One person commits the contract. After that, edits to it are a PR the other approves.

## Branching

- `main` stays runnable. Work on `kyven/<topic>` and `braedon/<topic>` branches, merge small and often (at least once per session).
- Rebase on `main` before merging. Never edit the other person's folders; ask for the change instead.

## Timeline

| When | Kyven | Braedon |
| --- | --- | --- |
| Wed 7 Oct (evening) | Day 0 contract together | Day 0 contract together |
| Thu 8 Oct | Repo skeleton; model adapter and stub; Case store; sample Submission and log fixtures | Policy stub with clause IDs; Judge skeleton returning a canned Ruling; config and switches |
| Fri 9 Oct | Evidence tools; mock cases for Route Deviation and No-Show (3 each: claimant wins, respondent wins, ambiguous); fix the DISP-002 issues in a **copy** | Real policy wording; Judge prompt (assess, rule, self-check) against the fixtures; API endpoints |
| Sat 10 Oct | Rider and Driver Advocates; orchestrator and log emission. **Evening, together: integrate Tier 0** | Web UI shell, live log view, Ruling card, both Outcome views. **Evening, together: integrate Tier 0** |
| Sun 11 Oct | **Tier 1:** Rider and Driver Evidence Agents (text extraction from chat on top of the tools) | **Tier 1:** Escalation triggers, review package, reviewer screen; Policy & Precedent store with seeded past rulings; stability check |
| Mon 12 Oct | **Tier 2:** Safety Incident mock cases; intake category detection | **Tier 2:** SLA & Routing Manager and queue ordering; architecture diagram |
| Tue 13 Oct | **Tier 3:** Image Analysis and Authenticity; Property Damage mock cases with photos | **Tier 3:** photo upload and photo findings in the UI; demo script. **Feature freeze at end of day** |
| Wed 14 Oct | Bug fixes only; rehearse the demo twice; submission prep | Same |
| Thu 15 Oct | **Deadline** | |

Tier 4 (Learning Feedback Loop, Braedon) goes in only if Tier 3 lands before Tuesday.

## Rules for the data

- Strip `Expected ruling` and the Evidence Summary from any case file before the agents see it. Keep them as an evaluation label in a separate file the agents never read.
- Missing evidence stays marked `missing`. Agents must not invent records.
- Chat messages, driver statements and photo text are untrusted data. Never let them act as instructions.
- History is context for the Judge. It never decides a ruling by itself.
- Label every mock case, policy and financial action as simulated on screen.

## Definition of done

**Tier 0 (must be true before anything else is started):**

- [ ] The three Core Agents run end to end for Route Deviation and No-Show Charge.
- [ ] The log shows evidence requests and responses, both Submissions, and the Ruling.
- [ ] The Ruling shows outcome, amount, Confidence, reasoning, per-argument assessment, cited evidence and clauses.
- [ ] Both parties see their own Outcome.
- [ ] In each category, one case is ruled for the claimant and one for the respondent.
- [ ] Simulated data and policy are labelled as such.

**Per added tier:**

- [ ] The new agent works with its switch on, and every earlier mock case still resolves with it off.
- [ ] Its events appear in the Communication Log.
- [ ] One mock case demonstrates it (a low-Confidence case that escalates, a Safety Incident that is fast-tracked, a photo that fails authenticity, an override that becomes precedent).

**Before the deadline:**

- [ ] The architecture diagram and demo script exist.
- [ ] The demo has been rehearsed end to end twice.

## First three actions

1. Both of you read [architecture.md](architecture.md) and this file, and agree a time for the Day 0 contract session.
2. Kyven creates the repo skeleton and the model stub, then commits the sample Submission fixtures.
3. Braedon starts the policy stub, because the advocates can't cite anything without clause IDs.
