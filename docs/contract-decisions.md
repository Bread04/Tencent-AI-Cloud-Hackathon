# Contract session decisions

## Approved Route Deviation rule (2026-10-12)

Ticket 06 uses [ADR 0004](adr/0004-route-deviation-refund-rule.md): compare the
authoritative paid net receipt with the recomputed optimal net fare, cap the
refund at the paid amount, and round final SGD cents half-up. Route distances
use 0.001km and elapsed time 0.01 minute precision. Incomplete, invalid or
unreconciled inputs require review. R-04, D-04, R-03 and D-03 and shared contract
fields are unchanged. Calculations carry provenance in existing fields.


**Status: proposed, pending confirmation with Kyven.** Nothing here has been agreed in a contract session yet. The values are the proposals in [architecture.md](architecture.md) (sections 5.7, 6.1, 6.2, 6.4), cross-checked against the `RULES` object in `prototypes/judge-decision-logic.prototype.html`. They are the defaults the code runs on until both of us confirm or change them.

The code reads every value from `CONFIG` in [`src/config.py`](../src/config.py). Change a value there and here together. The contract types are in [`src/contracts.py`](../src/contracts.py).

## Proposed

### Confidence (architecture 6.1)

Confidence is a number from 0 to 1, calculated by code, and equal to the lowest of its components.

| Component | Value | `CONFIG` field |
| --- | --- | --- |
| Policy Fit | clear 0.95, arguable 0.75, unclear 0.5 | `confidence.policy_fit` |
| Evidence completeness | share of the category's material-evidence checklist that is available | (computed, no constant) |
| Consistency | 0.95 with no conflicts, 0.65 with a conflict on a material item | `confidence.consistency_no_conflict`, `confidence.consistency_conflict` |
| Stability (Tier 1) | 0.95 if both passes agree, 0.5 if not | `confidence.stability_agree`, `confidence.stability_disagree` |
| Authenticity (Tier 3) | 0.5 on a failed or unknown check on a photo that matters | `confidence.authenticity_failed_or_unknown` |
| Decisive Own Finding | caps Confidence at 0.75 | `confidence.decisive_own_finding_cap` |
| History step | lowers Confidence by 0.05 per rule that fires, at most 0.2 | `confidence.history_step`, `confidence.history_max` |

### Escalation (architecture 5.7)

- **Threshold:** a Ruling with Confidence below **0.7** is escalated (`escalation.confidence_threshold`).
- **Triggers:** any one of these escalates (`escalation.triggers`, the `ReviewTrigger` values):

| Trigger | When |
| --- | --- |
| `low_confidence` | Confidence below the threshold |
| `balanced_evidence` | Balance of Evidence is balanced |
| `policy_gap` | A Policy Gap (Policy Fit unclear) |
| `safety_incident` | The Dispute Category is Safety Incident |
| `authenticity_check` | Failed or unknown Authenticity Check on a photo that matters to the outcome |
| `stability_disagreement` | The two Judge passes disagree |
| `history_rule` | A History rule calls for review |
| `stage_failed` | A stage used up its retry budget |
| `amount_over_limit` | The Ruling amount is above the limit |

### Structured output (architecture 6.4 and 8)

- Model output is requested as **schema-constrained JSON** (`model.structured_output = "json_schema"`) and validated in code against the pydantic contract type.
- A reply that fails validation or the citation rules gets up to **2 repair attempts** with the error fed back (`model.repair_attempts`), then the stage fails to review.
- The adapter is one function: `complete(messages, *, case_id, agent, schema=None, images=None)`. With `schema` it returns a validated object, without it plain text.

### Switches (architecture 6.3)

One switch per Supporting Agent, **all off by default** (`CONFIG.switches`): `evidence_agents`, `policy_precedent`, `image_analysis`, `escalation`, `sla_routing`, `learning_loop`. A Case records the switches in force when it was filed.

### Material evidence for No-Show Charge (architecture 6.1)

`driver_at_pickup`, `arrival_vs_scheduled`, `wait_timers`, `contact_attempts`, `rider_position` (`CONFIG.material_evidence`).

### Contract types (architecture 4)

Fields follow the architecture table. Choices made while writing the types:

- Unknown fields are rejected on every object.
- Money (`Ruling.amount`, `Calculation.result`) is `Decimal`, not float. Currency is `SGD`.
- Claimant and Respondent are derived from `Dispute.filed_by`, not stored, so they cannot disagree with it.
- The Remedy list is closed: `full_refund`, `partial_refund`, `fee_reversal`, `compensation_to_driver`, `no_action`.
- A Ruling with an amount must state a currency and a calculation, and the amount must equal the calculation result.
- A Ruling that names a Policy Gap must have Policy Fit `unclear`.
- `Ruling.confidence` is empty in the Judge's draft and filled in by code; a `final` Ruling must have it.
- An Evidence Item with status `conflicting` must list what it conflicts with.
- A Precedent from a `human_override`, and a review record that overrides, must carry a reason.
- A Case holds at most one Submission per advocate.

## Open

Placeholders the code currently runs on. Each needs a decision.

| # | Question | Placeholder in the code |
| --- | --- | --- |
| ~~1~~ | ~~Ruling amount limit for the `amount_over_limit` trigger.~~ Confirmed 13 Oct 2026: SGD 50.00. | — |
| ~~2~~ | ~~History rule table.~~ Confirmed 13 Oct 2026: `prior_rejected` lowers at ≥ 3 and also triggers review at ≥ 5; `late_cancel_flag` lowers on the flag; step 0.05, cap 0.2. | — |
| ~~3~~ | ~~Stability margin.~~ Confirmed 13 Oct 2026: 0.1. | — |
| ~~4~~ | ~~Material-evidence checklists for Route Deviation, Property Damage and Safety Incident.~~ Resolved: all four categories are defined in `CONFIG.material_evidence`. | — |
| ~~5~~ | ~~How a checklist line is matched to Evidence Items.~~ Resolved: `CHECKLIST_SOURCES` in `src/agents/judge/numbers.py` maps each key to its `source`. | — |
| 6 | **Citing missing evidence.** Rule 2 says a `missing` item can be cited only as missing. | Added `missing_evidence_ids` to Submission and Ruling (not in the architecture table); every other evidence citation is treated as fact |
| ~~9~~ | ~~`Case.priority` scale and direction.~~ Resolved: category points (Safety 100 > Property 40 > Route 30 > No-Show 20) plus urgency and amount; higher is more urgent (`src/agents/routing.py`). | — |
| ~~10~~ | ~~Model provider, including a vision-capable model.~~ Resolved 13 Oct 2026: Google Gemini (`gemini-3.5-flash-lite`), vision-capable, via its OpenAI-compatible endpoint (ticket 08). | — |
| ~~11~~ | ~~Per-argument identity.~~ Resolved 13 Oct 2026: arguments carry a code-assigned reference (`rider_advocate#counter-1`), and the `ArgumentAssessment` stores it as `argument_ref`. | — |
| ~~12~~ | ~~Recomputing the amount needs the policy formula.~~ Resolved: `amount_for` in `src/agents/judge/numbers.py` recomputes it by ADR 0004; the Judge cites the calculation. | — |
| ~~13~~ | ~~Evidence Item kind.~~ Resolved 13 Oct 2026: `EvidenceSource` (a `StrEnum`) closes the `source` list. | — |
| ~~14~~ | ~~Case IDs and the stub script.~~ Resolved: `ReplayModel` (`src/api/demo.py`) resolves scripts by `dispute_id`, so mock cases do not depend on creation order. | — |
| 15 | **Claimant and Respondent** are derived from `filed_by` rather than stored, so a fixture that carries `claimant` is rejected. | Derived properties |
| 16 | **Where citation rules run.** `citation_errors` is called by the agents (so they can repair), not by the store on `add_submission` or `set_ruling`. | Agents call it |
| ~~17~~ | ~~Invalid Dispute Category.~~ Resolved: intake rejects with a 422 and reason before a Case exists; a Case that is later rejected emits `case_rejected` via `store.reject` (ticket 19). | — |
| 18 | Still open from architecture section 12 and untouched here: precedent similarity (now decided: tags first, optional embedding rerank, see architecture 5.3), mock policy wording, timeouts per stage. | |
| ~~9~~ | ~~Where the Route Deviation refund formula lives.~~ Resolved: ADR 0004 defines it; `amount_for` implements it. | — |

## Confirmed (Braedon, 13 Oct 2026)

All open items above are now resolved. The four remaining placeholders were confirmed as follows, implemented where they needed code:

- **1 — Amount limit:** SGD 50.00 (unchanged; documented in `config.py`).
- **2 — History rules:** `prior_rejected` lowers Confidence at ≥ 3 and also adds a `history_rule` trigger at ≥ 5; `late_cancel_flag` lowers on the flag; step 0.05, cap 0.2. The ≥ 5 trigger is in `src/agents/judge/history.py`.
- **3 — Stability margin:** 0.1 (unchanged).
- **11 — Argument identity:** arguments already carry a code-assigned reference (`rider_advocate#counter-1`); the `ArgumentAssessment` now stores it as `argument_ref`.

Items 6, 15, 16 and 18 are effectively decided in the "Decided" section below and only need a wording note (mock policy + per-stage timeouts, item 18). This session also closed the tag gap behind item 4: `case_tags` now emits tags for Route Deviation and Property Damage, so the two seeded Route Deviation Precedents are reachable again.

## Decided (Braedon, 11 Oct 2026, for Kyven to confirm)

- **Policy is not role-scoped.** Every agent receives the same clause set, both sides' clauses included, from one version (architecture 5.3). `PolicyClause` gets no `role` field. Kyven's Rider and Driver Policy Agents become roles of the one Policy & Precedent Agent (ticket 10).
- **The contract is extended** (ticket 18): `Dispute` keeps the original report and its incident, category-detail and requested-resolution fields; `Submission` records the report, evidence and policy versions it was built from; the Case can seal a new evidence version after a policy gap, which invalidates the earlier Submissions and Ruling.
- **Kyven's JavaScript agents are ported to Python**, not called from it (tickets 10 and 11).
- **The shared repair loop** is one helper in `src/llm/`, built in ticket 04 and reused by 05 and 08.
- **Thresholds come from trip data** (ADR 0002).
- **Escalation (ticket 09, Braedon, 12 Oct 2026, for Kyven to confirm).** Confidence is checked after the History step, so a Ruling that History pulls below the threshold is held. The History step is 0.05 per rule (was 0.1; `confidence.history_step`, max still 0.2) so the DISP-002 demo case lands on exactly 0.70 and resolves, while DISP-004 escalates. Escalation is on by default in `CONFIG.switches`; with it off every Ruling finalizes. A reviewer can confirm a proposal, or override it with a required reason, which reverses the outcome (No-Show is binary) and recomputes the amount. A Case held because a stage failed has no Ruling, so it appears in the queue but cannot be confirmed or overridden.
- **Model calls are recorded and shown (Braedon, 12 Oct 2026, for Kyven to confirm).** `LogEventKind` gains `model_call`: one Communication Log row per request to the model. The detail (what was sent, the reply, timing, attempt number, why a call was sent back) lives in the Case store as `ModelCall` (`src/llm/calls.py`), not in the shared contract, and the console shows it on a Model calls tab. The orchestrator wraps the model in `RecordingModel` for every run. The Judge now also logs `argument_assessed`, one row per argument.
- **Precedents (ticket 10, Braedon, 12 Oct 2026, for Kyven to confirm).** `PrecedentSource` gains `seeded` and `human_confirmed` (ADR 0003); `model` stays but is never retrievable. A new `CONFIG.precedents` holds `retrieval` (tags or embeddings, default tags) and `limit` (3). The Judge's draft gains `cited_precedent_ids` and `precedent_departure`; a Remedy that differs from a shown Precedent needs the explanation. The switch is `switches.policy_precedent`, off by default.
- **Stability check (ticket 12, Braedon, 12 Oct 2026, for Kyven to confirm).** `Switches` gains `stability_check` (off by default). With it on, the Judge's Confidence gains a `stability` component (0.95 agree, 0.5 disagree) and a disagreement adds the `stability_disagreement` Review Trigger. The Judge's first-pass Submission order is set by the Case ID. The margin is the existing `confidence.stability_margin`.
- **SLA routing and Safety Incidents (ticket 13, Braedon, 12 Oct 2026, for Kyven to confirm).** `Case.priority` is set only with `switches.sla_routing` (off by default; otherwise 0). Safety Incident is resolvable only with that switch on, uses the clauses R-05, R-06, D-05, D-06, the remedies full_refund or no_action, and is always held for review. The two Safety Incident mock cases (DISP-008, DISP-009) are rider-filed. Priority points are placeholders.
  Also added with ticket 13: material-evidence checklist entries for Safety Incident in `CONFIG.material_evidence` (`trip_route`, `conversation`, mapped to the GPS and chat items in `src/agents/judge/numbers.py`), `src/agents/intake.py` (keyword classification when no category is chosen) and `POST /api/classify`. Nothing files a Dispute through the classifier yet; ticket 19 (filing from the report form) is where it is called.
- **Evidence Agents (ticket 11, Braedon, 12 Oct 2026, for Kyven to confirm).** No contract change: extracted facts are ordinary `EvidenceItem`s (`source` `extracted_fact`, IDs `EV-FACT-RIDER-n`, `EV-FACT-DRIVER-n`, `derived` holds `message_ref` and `quote`; a failed agent leaves `EV-FACTS-<SIDE>-1` and a failed tool `EV-TOOLS-1`, both `missing` with the cause). Switch `evidence_agents` stays off by default. References are `EV-CHAT-1#<position>`, `DISPUTE#description` and `DISPUTE#driver_statement`. New mock case DISP-010 (a chat message that tries to instruct the system). The demo gains a fourth switch, so there are 96 recorded streams.
- **Report fields, version references and resealing (ticket 18, Braedon, 13 Oct 2026, for Kyven to confirm).** This is the one change to the shared contract file that ticket 18 allows.
  - **Dispute.** Four optional fields, all empty for a Dispute that did not come from the report form, so every existing fixture still loads. `filed_report` is the report exactly as submitted (any JSON object, kept and never edited). `incident` is `time` (in `time_zone`; null when the party does not know it), `time_zone` (required) and `location`. `category_details` maps text to text. `requested_resolution` is `type` (required), `amount` (above zero, `Decimal`), `currency` (three capital letters, required with an amount) and `details`. Unknown or malformed fields in the three parsed objects are rejected by name; `filed_report` is the one deliberate exception to "unknown fields are rejected", because it is a copy, not a contract object. `requested_remedy` stays as the one-line wording. "Requested Resolution" is the party's request and is a different thing from the Remedy a Ruling grants (both are now in the GLOSSARY).
  - **The raw report is not sent to a model.** The advocates and the Judge get the Dispute without `filed_report`; the advocates' prompt labels the three parsed fields as untrusted party text.
  - **Case versions.** `Case` gains `report_version` (`<case>-report-v1`, set when the Case is created) and `policy_version` (the one version its Policy Clauses share; the store refuses clauses of mixed versions), next to the existing `evidence_version`. `Case.versions` gives the three together.
  - **Submission.** Gains `report_version`, `evidence_version` and `policy_version`. Code stamps them from the snapshot the advocate read, overwriting anything the model wrote. `add_submission` refuses a Submission that states a version other than the one in force. A version left empty is not checked, so older fixtures and hand-built Submissions still file; the advocates always state all three. Once a Case has been resealed, a Submission must state its evidence version.
  - **Resealing.** `CaseStore.reseal_evidence(case_id, items, reason)` adds at least one new Evidence Item and seals `<case>-evidence-v2` in one write with one `evidence_resealed` Log event (new `LogEventKind`) that names both versions, the new items, the reason and what went stale. It is allowed once per Case, only after the first seal, only with a stated reason, and not once a final Ruling stands. The store does not check that a Policy Gap was the cause; the caller says so in the reason. `Case.superseded_evidence_versions` keeps the earlier version.
  - **Stale means moved, not flagged.** On a reseal the Case's Submissions and Ruling move to `Case.stale_submissions` and `Case.stale_ruling`, `submissions` and `ruling` are emptied, and the status returns to `building_cases`. Code that reads `case.ruling` can therefore never act on a stale one. Outcomes already sent (a "review pending" notice) are left as sent.
  - **Not built here.** Nothing calls `reseal_evidence` yet: the orchestrator does not rerun the advocates and Judge after a Policy Gap. A Ruling carries no version, so `set_ruling` cannot tell a Ruling drafted from the first evidence version from a current one; whoever wires the rerun must not let the old Judge call finish into the new round. The Evidence Agents do not read the new Dispute fields yet. `time_zone` is any non-empty text (not checked against the zone list) and `currency` is any three capitals, looser than the report form's own check, which requires SGD. The report form filling the new Dispute fields is ticket 19. The recorded console streams were not re-recorded, so they lack the new fields. `PolicyClause` still has no `role`.

## Rider Python execution amendment (2026-10-12)

All deterministic Rider Evidence, Policy and Advocate rules run in
`src/agents/rider/`, reusing the existing Python route/fare calculator and shared
policy JSON. No shared Case, EvidenceItem, PolicyClause or Submission fields
change. The prototype result schema and exact original report are preserved.
The browser retains rendering, simulated ownership selection, session storage
and bounded async API calls only.

The trusted public `data/prototype/rider-catalog.json` supplies all eight current
Rider app trips; histories/evaluation labels are excluded. Python never accepts
client telemetry or policy. Requests are limited to 128 KiB/eight nesting levels
with nested metadata/finite-value validation. Rider selection is simulated
identity, not production authentication.

Case/evidence APIs register the generated public log on the server, bind an
opaque handle to the owner cookie and redact all log arrays. The existing access
gate and legacy client-log migration endpoint remain. Both Rider entry points
require FastAPI; offline requests preserve the report and show an explicit retry
without browser agent execution.
- **Photo findings and Property Damage (tickets 14 and 15, Braedon, 13 Oct 2026, for Kyven to confirm).** No contract change. Photo findings are `EvidenceItem`s (`source` `photo_finding`, IDs `EV-PHOTO-n-DESC`, `-TIME`, `-AI`; one `missing` `EV-PHOTO-n` if a photo could not be analysed; `derived.uncertainty` on each). Property Damage is resolvable (clauses R-07 and D-07; the Remedy is the existing `compensation_to_driver`). The cleaning-fee rule and the authenticity cap are in ADR 0005, and `CONFIG.cleaning_fee_cap` is new. The Judge's `confidence.components` gains `authenticity` (0.5) when a photo check fails or is unknown. Mock cases DISP-011 to 013 and mock photos in `data/photos/` (placeholder images with a sidecar `.json` for the capture time). The demo gains a fifth switch, Photo analysis, offered only for a Dispute with photos.
