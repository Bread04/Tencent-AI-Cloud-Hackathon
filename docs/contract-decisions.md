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
| 1 | **Ruling amount limit** for the `amount_over_limit` trigger. | SGD 50.00 (`escalation.amount_limit`) |
| 2 | **History rule table.** Which rules, and what counts as "several"? May a rule add a Review Trigger as well as lower Confidence? | Two rules from the prototype, each lowering Confidence by one step: `prior_rejected` (3 or more prior rejected disputes of the category) and `late_cancel_flag` (`CONFIG.history_rules`) |
| 3 | **Stability margin:** how far Confidence may differ between the two Judge passes before it counts as disagreement. | 0.1 (`confidence.stability_margin`) |
| 4 | **Material-evidence checklists** for Route Deviation, Property Damage and Safety Incident. | Not defined; only No-Show Charge exists |
| 5 | **How a checklist line is matched to Evidence Items.** The architecture's Evidence Item has no `kind` field. | None; `MaterialEvidenceEntry.evidence_ids` is filled by whoever builds the checklist |
| 6 | **Citing missing evidence.** Rule 2 says a `missing` item can be cited only as missing. | Added `missing_evidence_ids` to Submission and Ruling (not in the architecture table); every other evidence citation is treated as fact |
| 9 | **`Case.priority`:** scale and direction. | Integer, default 0, meaning not yet agreed |
| 10 | **Model provider**, including a vision-capable model. | None; only the offline stub exists (ticket 08) |
| 11 | **Per-argument identity.** An Argument Assessment refers to an argument by its text and its author; a Submission has no argument IDs. | Text plus author |
| 12 | **Recomputing the amount** (rule 3) from fare Evidence Items needs the policy formula. | The contract only checks amount against the shown calculation; recomputation is left to the Judge ticket |
| 13 | **Evidence Item kind.** `source` is free text, so withholding History from the Judge (architecture 6.2) and matching checklist lines both rely on string matching. Should `source` be a closed list (gps, chat, fare, history, trip, photo, driver statement)? | Free text |
| 14 | **Case IDs and the stub script.** Case IDs are numbered in creation order and the stub is keyed on (case ID, agent), so a mock-case script depends on the order cases are created. Key on the dispute ID instead? | `CASE-0001`, `CASE-0002`, … |
| 15 | **Claimant and Respondent** are derived from `filed_by` rather than stored, so a fixture that carries `claimant` is rejected. | Derived properties |
| 16 | **Where citation rules run.** `citation_errors` is called by the agents (so they can repair), not by the store on `add_submission` or `set_ruling`. | Agents call it |
| 17 | **Invalid Dispute Category.** It fails contract validation before a Case exists, so no `case_rejected` event is logged for it. Intake needs to decide how to show that rejection. | Validation error |
| 18 | Still open from architecture section 12 and untouched here: precedent similarity (now decided: tags first, optional embedding rerank, see architecture 5.3), mock policy wording, timeouts per stage. | |
| 9 | **Where the Route Deviation refund formula lives.** The shared policy set has none (see ADR 0002). | Not defined |

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
- **SLA routing and Safety Incidents (ticket 13, Braedon, 12 Oct 2026, for Kyven to confirm).** `Case.priority` is set only with `switches.sla_routing` (off by default; otherwise 0). Safety Incident is resolvable only with that switch on, uses the clauses R-05, R-06, D-05, D-06, the remedies full_refund or no_action, and is always held for review. The two Safety Incident mock cases (DISP-005, DISP-006) are rider-filed. Priority points are placeholders.
  Also added with ticket 13: material-evidence checklist entries for Safety Incident in `CONFIG.material_evidence` (`trip_route`, `conversation`, mapped to the GPS and chat items in `src/agents/judge/numbers.py`), `src/agents/intake.py` (keyword classification when no category is chosen) and `POST /api/classify`. Nothing files a Dispute through the classifier yet; ticket 19 (filing from the report form) is where it is called.
- **Evidence Agents (ticket 11, Braedon, 12 Oct 2026, for Kyven to confirm).** No contract change: extracted facts are ordinary `EvidenceItem`s (`source` `extracted_fact`, IDs `EV-FACT-RIDER-n`, `EV-FACT-DRIVER-n`, `derived` holds `message_ref` and `quote`; a failed agent leaves `EV-FACTS-<SIDE>-1` and a failed tool `EV-TOOLS-1`, both `missing` with the cause). Switch `evidence_agents` stays off by default. References are `EV-CHAT-1#<position>`, `DISPUTE#description` and `DISPUTE#driver_statement`. New mock case DISP-007 (a chat message that tries to instruct the system). The demo gains a fourth switch, so there are 96 recorded streams.

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
