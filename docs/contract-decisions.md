# Contract session decisions

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
| History step | lowers Confidence by 0.1 per rule that fires, at most 0.2 | `confidence.history_step`, `confidence.history_max` |

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
| 7 | **`Dispute.requested_remedy`:** free text, or one of the closed Remedy list? | Free text |
| 8 | **`Precedent.ruling`:** a full Ruling, or a shorter summary (outcome, Remedy, amount)? A full Ruling makes seeding mock precedents heavier. | Full `Ruling` |
| 9 | **`Case.priority`:** scale and direction. | Integer, default 0, meaning not yet agreed |
| 10 | **Model provider**, including a vision-capable model. | None; only the offline stub exists (ticket 08) |
| 11 | **Per-argument identity.** An Argument Assessment refers to an argument by its text and its author; a Submission has no argument IDs. | Text plus author |
| 12 | **Recomputing the amount** (rule 3) from fare Evidence Items needs the policy formula. | The contract only checks amount against the shown calculation; recomputation is left to the Judge ticket |
| 13 | Still open from architecture section 12 and untouched here: precedent similarity (tags or embeddings), mock policy wording, timeouts per stage. | |
