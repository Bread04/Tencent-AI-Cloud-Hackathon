
# Waypoint — AI dispute resolution for Ryde

Waypoint resolves ride-hailing disputes through two independent advocate agents and an impartial Judge. It gathers trip evidence, applies shared policy, produces an auditable ruling, and sends uncertain or safety-related cases to a human reviewer.

**Submission blurb:** Fair, explainable outcomes for rider–driver disputes.

**Hackathon track:** Digital Native — Ryde. **Challenge:** Multi-Agent Autonomous Dispute Resolution System.

<video src="https://cdn.jsdelivr.net/gh/Bread04/Tencent-AI-Cloud-Hackathon@main/brag-output/film.mp4" controls width="100%"></video>

## Project overview

**Users.** Ryde support reviewers who resolve rider–driver disputes, and the riders and drivers who receive the decision with an explanation.

**Target scenarios.** Four dispute categories: Route Deviation ("the driver took a longer route and I was overcharged"), No-Show Charge, Property Damage / Mess, and Safety Incident.

**Value proposition.** Cut the time reviewers spend gathering and reconciling GPS, chat, photo, fare and policy evidence, while keeping every decision traceable, consistent and safely escalated. Both parties get the same explained outcome in party-specific wording.

## Real-world scenario insights

- **Pain points.** The hackathon challenge statement describes thousands of daily tickets that are complex, subjective and emotionally charged, reviewed by hand across GPS telemetry, chat logs, photos, payments and policy. It cites high support cost, 24–72 hour resolution, inconsistent rulings between agents, and churn when users feel unfairly treated. These are the organizer's figures, not independently verified measurements.
- **Regulatory context.** Singapore's LTA says private-hire fares should be shown before a trip and that fare-evasion and overcharging rules apply to app-booked trips ([LTA: Getting a Ride](https://www.lta.gov.sg/content/ltagov/en/getting_around/point_to_point_transport_and_cross_border_services/getting_a_ride.html)). That supports the need for transparent, evidence-based review.
- **Core problems solved.** Slow manual evidence comparison; inconsistent outcomes on similar cases; opaque decisions; and the risk of automating sensitive cases (safety incidents always go to a human).

## Solution design

**Business architecture.** A reviewer files a case. Waypoint prioritizes it, gathers evidence, produces a cited ruling, and either issues it to both parties or sends it to a human review queue. Refunds and compensation are recommendations only; no payment is executed.

**Technical architecture.** A fixed, code-driven pipeline (`src/orchestrator/`) runs each dispute: code validates and prioritizes the case, retrieves simulated records and seals a versioned evidence set. The Rider Advocate and Driver Advocate then work from the same sealed evidence and policy, and the Judge reviews both submissions. See the [architecture diagram](docs/diagrams/architecture.html) and [docs/architecture.md](docs/architecture.md).

**How prompts drive the AI generation.** The Rider and Driver Advocate prompts use the same evidence and policy but assign opposite roles. Each directs the model to produce a structured argument, cite only supplied evidence IDs, address a counterargument, and treat party-written text as data rather than instructions. The Judge prompt receives both submissions and the original evidence and requests a cited, reasoned assessment of each argument. Prompts live in `src/agents/advocates/` and `src/agents/judge/`. Code then validates schemas and citations and calculates amounts and confidence, so the model never computes money or confidence. Every stage appears in the Communication Log.

## Business value

The value hypothesis is less active reviewer time per case without losing traceability or safe escalation. **No pilot data exists yet.** The figures below are a worked model with placeholder inputs for Ryde to replace, not measurements.

| Input | Placeholder |
| --- | --- |
| Disputes per day (D) | 1,000 (the brief says "thousands") |
| Share in the four supported categories (S) | 80% |
| Share needing human review (H) | 35% |
| Active reviewer minutes per case today (Tb) | 15 |
| Active reviewer minutes per case with Waypoint (Tw) | 4 (read the sealed evidence and ruling) |

Time saved per day = D × S × (1 − H) × (Tb − Tw) + D × S × H × (Tb − Tw) × 0.5, where human-reviewed cases get half the saving because they still skip evidence gathering. With the placeholders: 5,720 + 1,540 = **about 7,260 reviewer minutes (about 121 hours) a day**.

Benefits that do not depend on those inputs: every ruling carries cited evidence IDs, a code-calculated amount and a confidence value; both parties see the same decision; safety incidents escalate to a human by rule ([ADR 0006](docs/adr/0006-safety-incidents-escalate-by-rule.md)).

**Pilot metrics to prove the model:** median active reviewer minutes per case versus baseline; filing-to-first-decision time; share of rulings overturned by a human; citation validity; safety cases escalated (target 100%); repeat-dispute and churn rates after a decision.

## Verified results

Run from the repository root:

```powershell
uv run pytest
$env:MODEL_PROVIDER = "stub"
uv run python -m scripts.evaluate
uv run python -m scripts.rehearse
```

Verified on this working tree: 830 tests passed, 12 of 12 prepared cases matched their expected labels with scripted replies, and 11 of 11 walkthrough steps ended as scripted. This shows repeatable fixture behavior, not live-model accuracy or production reliability.

## Stretch goals

| Capability | Status |
| --- | --- |
| Evidence collection | Implemented with simulated evidence tools and optional party-side extraction agents. |
| Policy and precedent | Implemented with a prepared precedent store; optional local embeddings can rank records. |
| Image analysis | Implemented for supplied mock photos; uncertainty is retained in the evidence. |
| Escalation and human review | Implemented for safety cases, low confidence and configured triggers. |
| Learning from human overrides | Implemented as an optional override-to-precedent path. |
| SLA and priority routing | Implemented as code-based priority scoring. |
| Fraud and bad-faith detection | Not implemented. |

## Development process and AI tooling

<!-- TODO (team): describe genuine CodeBuddy / WorkBuddy usage here and attach the conversation screenshots (minimum 3). Do not add claims that did not happen. -->

Claude Code was used under the team's direction to write and review code, tests and tickets; every change was run against the test suite. The architecture and walkthrough diagrams were generated with the open-source Archify skill from the architecture document and running code. The console's pipeline stepper and confidence gauge were ported to plain HTML/CSS/JS from two public 21st.dev components. Layout, colours and fonts come from the Waypoint rider-app prototype in `prototypes/`.

## Data and limitations

All trips, GPS records, messages, photos, policy, precedents and payment actions are simulated; no real Ryde data is used and the system does not connect to Ryde production systems. Refunds and compensation are recommendations only.

## Run the prototype

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --locked --group dev
uv run uvicorn src.api.demo:app
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and choose a prepared dispute. The default model uses scripted replies, so the demo runs offline without an API key. To run the automated suite, use `uv run pytest`.

After a run, open `/evaluation` to compare outcomes against the separate expected-case labels.

## What the system does

| Stage | What happens |
| --- | --- |
| Evidence | The system collects GPS, chat, fare and trip-history records, marks missing evidence, and seals a shared evidence set. |
| Rider Advocate | Builds an independent rider Submission grounded in the evidence and policy. |
| Driver Advocate | Builds an independent driver Submission from the same sealed evidence and policy. |
| Judge | Reviews both Submissions against the original evidence, checks citations, explains each decision, and calculates confidence. |
| Outcome or review | Both parties receive the same ruling in party-specific wording. Uncertain or safety cases go to a human review queue. Refunds are recommendations; the demo never moves money. |

The live Communication Log shows evidence requests, agent submissions, model calls, citations, and the ruling as they happen. Switches let judges see the three required agents first, then turn on supporting features individually.

## Handbook requirements and evidence

| Requirement | Where to see it |
| --- | --- |
| Rider Advocate, Driver Advocate, Judge | `src/agents/advocates/`, `src/agents/judge/` |
| Two or more dispute categories | No-Show: DISP-002/003; Route Deviation: DISP-008/009/010. Prepared cases also cover Property Damage and Safety Incidents. |
| Observable agent communication | Run the demo and open the Communication Log. |
| Working prototype | Start the FastAPI app using the commands above. |
| Architecture diagram | [Open the interactive architecture](docs/diagrams/architecture.html) or [view the image](docs/diagrams/architecture.png). |
| Demo walkthrough | [Live demo](https://ryde-dispute-resolution.vercel.app) and [the presenter script](docs/demo-script.md). |
| Source code | This repository; see the [project structure](#project-structure). |

There are 12 prepared disputes across the four supported categories. The expected outcomes are kept in separate evaluation files that the agents cannot read.

## Recommended demo order

**Live demo:** [ryde-dispute-resolution.vercel.app](https://ryde-dispute-resolution.vercel.app) (scripted replies; no setup needed).

Start with the core agents and show that the system can rule for either side. Then demonstrate Route Deviation to make the second required category explicit. Finally, enable the supporting features to show precedent, safety escalation, image analysis, and learning from a human override.

1. Run **DISP-003** with optional switches off: uphold the rider's No-Show claim and recommend a SGD 5.00 fee reversal.
2. Run **DISP-002** with optional switches off: reject the rider's No-Show claim and rule for the driver.
3. Run **DISP-008**: show the Route Deviation calculation and a recommended partial refund of SGD 5.39.
4. Follow [the full walkthrough](docs/demo-script.md) for optional agents and human review. `uv run python -m scripts.rehearse` rehearses the prepared sequence with scripted replies.

## What uses AI, code, and simulated data

| Part | Implementation |
| --- | --- |
| Advocates and Judge | Model calls produce structured arguments and rulings. Code validates schemas, citations, and required assessments; an independent self-check tests whether cited evidence supports its claims. |
| Evidence and money | Ordinary code calculates route distances, waits, fare comparisons, refund amounts, confidence components, and queue priority. The model does not calculate money or confidence. |
| Policy and precedent | A shared mock policy and prepared precedent store are used. Retrieval is deterministic by default; optional local embeddings can rank precedents. |
| External records and actions | Trips, GPS, messages, photos, policy, and payments are simulated. A ruling may recommend an action, but no payment is executed. |

The live model is optional. Configure the OpenAI-compatible provider in `.env` using the settings in [.env.example](.env.example). The scripted model remains the reliable presentation default.

## Project structure

| Path | Contents |
| --- | --- |
| `src/agents/` | Advocates, Judge, evidence, policy, image analysis, escalation, and routing. |
| `src/orchestrator/` | Fixed, code-driven pipeline that runs each dispute. |
| `src/contracts.py` | Typed Case, evidence, Submission, Ruling, and Communication Log records. |
| `src/api/` | FastAPI demo, review queue, Rider endpoints, and web interface. |
| `data/cases/`, `data/policy/`, `data/precedents/` | Simulated cases and shared policy/precedent data. |
| `tests/` | Automated tests and scripted end-to-end evaluation. |
| `docs/architecture.md` | Architecture and implementation details. |
| `docs/demo-script.md` | Presenter instructions and narration. |

The separate Rider experience is at [`prototypes/`](prototypes/index.html); its backend-backed setup notes are in [docs/rider-usage.md](docs/rider-usage.md). It complements the dispute console and is not the primary multi-agent demo.

## Route Deviation details

The console and Rider report sample selector include DISP-008 (supported excess fare), DISP-009 (a rider-requested detour), and DISP-010 (unclear consent). Python computes route distances, stop candidates, duration differences, and reconciled fare comparisons. The Rider workflow reads curated public data and prepares a Submission; it does not issue a Judge ruling or execute a refund. [ADR 0004](docs/adr/0004-route-deviation-refund-rule.md) records the approved calculation.
