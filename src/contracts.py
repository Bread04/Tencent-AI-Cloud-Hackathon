"""The shared contract (architecture.md section 4).

Shared file: change it only with both teammates' agreement.
Names follow GLOSSARY.md. Unknown fields are rejected so typos fail loudly.
Every object round-trips through JSON, so fixtures and model output can be
loaded with `Model.model_validate_json(...)`.
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    """Base for every contract object."""

    model_config = ConfigDict(extra="forbid")


Text = Annotated[str, Field(min_length=1)]
Score = Annotated[float, Field(ge=0, le=1)]


# --- Vocabulary --------------------------------------------------------------


class Party(StrEnum):
    RIDER = "rider"
    DRIVER = "driver"

    @property
    def other(self) -> "Party":
        return Party.DRIVER if self is Party.RIDER else Party.RIDER


class DisputeCategory(StrEnum):
    ROUTE_DEVIATION = "route_deviation"
    NO_SHOW_CHARGE = "no_show_charge"
    PROPERTY_DAMAGE = "property_damage"
    SAFETY_INCIDENT = "safety_incident"


class CaseStatus(StrEnum):
    """Case lifecycle, architecture.md section 3.1."""

    FILED = "filed"
    REJECTED = "rejected"
    PRIORITISED = "prioritised"
    GATHERING_EVIDENCE = "gathering_evidence"
    BUILDING_CASES = "building_cases"
    JUDGING = "judging"
    PENDING_REVIEW = "pending_review"
    RULED = "ruled"
    NOTIFIED = "notified"
    CLOSED = "closed"


class EvidenceSide(StrEnum):
    RIDER = "rider"
    DRIVER = "driver"
    SHARED = "shared"


class EvidenceStatus(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    CONFLICTING = "conflicting"


class EvidenceSource(StrEnum):
    """The closed vocabulary of Evidence Item `source` kinds (architecture 6.2; contract open item 13).

    Closing this list makes History-withholding and checklist matching exact
    (no string matching against a free-text field).
    """

    GPS = "gps"
    CHAT = "chat"
    FARE = "fare"
    HISTORY = "history"
    RIDER_LOCATION = "rider_location"
    ROUTE = "route"
    DAMAGE_CLAIM = "damage_claim"
    TRIP = "trip"
    PHOTO_FINDING = "photo_finding"
    EXTRACTED_FACT = "extracted_fact"
    TOOLS = "tools"


class Advocate(StrEnum):
    RIDER_ADVOCATE = "rider_advocate"
    DRIVER_ADVOCATE = "driver_advocate"


class PrecedentSource(StrEnum):
    """Where a Precedent came from (ADR 0003). Only the last three are retrievable: an unreviewed `model` Ruling is not."""

    MODEL = "model"
    SEEDED = "seeded"
    HUMAN_CONFIRMED = "human_confirmed"
    HUMAN_OVERRIDE = "human_override"


class RulingStatus(StrEnum):
    FINAL = "final"
    PROPOSAL = "proposal"


class RulingOutcome(StrEnum):
    """Of the Claimant's claim."""

    UPHOLD = "uphold"
    PARTIALLY_UPHOLD = "partially_uphold"
    REJECT = "reject"


class BalanceOfEvidence(StrEnum):
    CLAIMANT = "claimant"
    RESPONDENT = "respondent"
    BALANCED = "balanced"


class Remedy(StrEnum):
    """The closed list defined in policy."""

    FULL_REFUND = "full_refund"
    PARTIAL_REFUND = "partial_refund"
    FEE_REVERSAL = "fee_reversal"
    COMPENSATION_TO_DRIVER = "compensation_to_driver"
    NO_ACTION = "no_action"


class ArgumentVerdict(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNPROVEN = "unproven"
    NOT_DECISIVE = "not_decisive"


class PolicyFit(StrEnum):
    CLEAR = "clear"
    ARGUABLE = "arguable"
    UNCLEAR = "unclear"


class ReviewTrigger(StrEnum):
    """Escalation triggers, architecture.md section 5.7."""

    LOW_CONFIDENCE = "low_confidence"
    BALANCED_EVIDENCE = "balanced_evidence"
    POLICY_GAP = "policy_gap"
    SAFETY_INCIDENT = "safety_incident"
    AUTHENTICITY_CHECK = "authenticity_check"
    STABILITY_DISAGREEMENT = "stability_disagreement"
    HISTORY_RULE = "history_rule"
    STAGE_FAILED = "stage_failed"
    AMOUNT_OVER_LIMIT = "amount_over_limit"


class ActionStatus(StrEnum):
    RECOMMENDED = "recommended"
    PENDING_REVIEW = "pending_review"
    EXECUTED = "executed"
    FAILED = "failed"


class ReviewDecision(StrEnum):
    CONFIRM = "confirm"
    OVERRIDE = "override"


class LogEventKind(StrEnum):
    """Communication Log event kinds, architecture.md section 9."""

    CASE_FILED = "case_filed"
    CASE_REJECTED = "case_rejected"
    PRIORITY_SET = "priority_set"
    EVIDENCE_REQUESTED = "evidence_requested"
    EVIDENCE_RETURNED = "evidence_returned"
    EVIDENCE_SEALED = "evidence_sealed"
    EVIDENCE_RESEALED = "evidence_resealed"  # a second evidence version; what was built on the first is now stale
    PHOTO_ANALYSED = "photo_analysed"
    POLICY_RETRIEVED = "policy_retrieved"
    PRECEDENT_RETRIEVED = "precedent_retrieved"
    SUBMISSION_FILED = "submission_filed"
    ARGUMENT_ASSESSED = "argument_assessed"
    RULING_DRAFTED = "ruling_drafted"
    MODEL_CALL = "model_call"  # one request to the model: who, how long, retry or not (the detail is in the Case store)
    SELF_CHECK_PASSED = "self_check_passed"
    SELF_CHECK_FAILED = "self_check_failed"
    STABILITY_CHECK = "stability_check"
    ESCALATED = "escalated"
    REVIEW_DECISION = "review_decision"
    OUTCOME_SENT = "outcome_sent"
    PRECEDENT_ADDED = "precedent_added"


# --- Switches ----------------------------------------------------------------


class Switches(Contract):
    """One on/off switch per Supporting Agent (architecture.md section 6.3).

    All off is the Tier 0 MVP: the three Core Agents alone.
    The values in force by default live in `src/config.py`.
    """

    evidence_agents: bool = False
    policy_precedent: bool = False
    image_analysis: bool = False
    escalation: bool = False
    stability_check: bool = False  # the Judge rules twice with the Submission order swapped (architecture 6.7)
    sla_routing: bool = False
    learning_loop: bool = False


# --- Dispute -----------------------------------------------------------------


class Incident(Contract):
    """When and where the reported incident happened, as the party stated it."""

    time: datetime | None  # in `time_zone`; None when the party does not know the time
    time_zone: Text
    location: str | None = None


class RequestedResolution(Contract):
    """What the party asked for on the report form. The Ruling's Remedy and amount are decided separately."""

    type: Text
    amount: Decimal | None = Field(default=None, gt=0)
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] | None = None
    details: str | None = None

    @model_validator(mode="after")
    def _amount_states_its_currency(self):
        if self.amount is not None and not self.currency:
            raise ValueError("a requested amount must state its currency")
        return self


class Dispute(Contract):
    dispute_id: Text
    trip_id: Text
    filed_by: Party
    category: DisputeCategory
    description: Text
    requested_remedy: Text
    filed_at: datetime
    photos: list[str] = []
    driver_statement: str | None = None
    # From the report form (ticket 18). All empty for a Dispute that was not filed through it.
    filed_report: dict[str, Any] | None = None  # the report exactly as it was submitted; kept, never edited
    incident: Incident | None = None
    category_details: dict[str, str] = {}
    requested_resolution: RequestedResolution | None = None

    @property
    def claimant(self) -> Party:
        return self.filed_by

    @property
    def respondent(self) -> Party:
        return self.filed_by.other


# --- Evidence and policy -----------------------------------------------------


class EvidenceItem(Contract):
    """One citable record. Missing data is an item with status `missing`
    (content says why), never an absent item."""

    evidence_id: Text
    source: EvidenceSource
    trip_id: Text
    side: EvidenceSide
    timestamp: datetime | None = None
    status: EvidenceStatus
    content: Any = None
    derived: dict[str, Any] = {}
    conflicts_with: list[str] = []

    @model_validator(mode="after")
    def _conflicting_items_are_linked(self):
        if self.status is EvidenceStatus.CONFLICTING and not self.conflicts_with:
            raise ValueError("an item with status 'conflicting' must list the IDs it conflicts with in conflicts_with")
        return self


class CounterArgument(Contract):
    argument: Text
    response: Text


class Submission(Contract):
    author: Advocate
    claim_restated: Text
    facts_relied_on: list[str] = []  # Evidence Item IDs cited as fact
    missing_evidence_ids: list[str] = []  # Evidence Item IDs cited only as missing
    counter_arguments: list[CounterArgument] = []
    policy_clause_ids: list[str] = []
    requested_outcome: Text
    # What it was built from (ticket 18): stamped by code from the Case snapshot the advocate read, never by the model.
    report_version: str | None = None
    evidence_version: str | None = None
    policy_version: str | None = None


class PolicyClause(Contract):
    clause_id: Text
    category: DisputeCategory
    text: Text
    version: Text


# --- Ruling ------------------------------------------------------------------


class Calculation(Contract):
    """How the amount was reached. Code computes `result`; the Judge only names the inputs."""

    formula: Text
    input_evidence_ids: list[str]
    result: Decimal


class ArgumentAssessment(Contract):
    author: Advocate  # whose Submission the argument came from
    argument_ref: str | None = None  # the argument's reference (`rider_advocate#counter-1`); set by code, never by the model
    argument: Text
    verdict: ArgumentVerdict
    reason: Text
    evidence_ids: list[str] = []  # the evidence it turned on


class OwnFinding(Contract):
    finding: Text
    evidence_ids: list[str]
    decisive: bool = False  # a decisive Own Finding caps Confidence


class Confidence(Contract):
    """Calculated by code, never self-reported by the Judge. `components` shows the working."""

    value: Score
    components: dict[str, Score]


class HistoryAdjustment(Contract):
    rule: Text
    reason: Text
    confidence_step: Annotated[float, Field(ge=0, le=1)] = 0  # how much Confidence was lowered


class MaterialEvidenceEntry(Contract):
    """One line of the category's material-evidence checklist. No evidence IDs means it was missing."""

    key: Text
    label: Text
    evidence_ids: list[str] = []

    @property
    def available(self) -> bool:
        return bool(self.evidence_ids)


class ReviewTriggerRecord(Contract):
    trigger: ReviewTrigger
    reason: Text


class Ruling(Contract):
    status: RulingStatus
    outcome: RulingOutcome
    balance_of_evidence: BalanceOfEvidence
    remedy: Remedy
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    calculation: Calculation | None = None
    argument_assessments: list[ArgumentAssessment] = []
    own_findings: list[OwnFinding] = []
    policy_fit: PolicyFit
    policy_fit_reason: Text
    policy_gap: str | None = None
    cited_evidence_ids: list[str] = []  # cited as fact
    missing_evidence_ids: list[str] = []  # cited only as missing
    cited_policy_clause_ids: list[str] = []
    cited_precedent_ids: list[str] = []
    reasoning_summary: Text
    confidence: Confidence | None = None  # filled in by code after the Judge's draft
    history_adjustments: list[HistoryAdjustment] = []
    material_evidence: list[MaterialEvidenceEntry] = []
    review_triggers: list[ReviewTriggerRecord] = []

    @model_validator(mode="after")
    def _amount_matches_its_calculation(self):
        if self.amount is None:
            return self
        if not self.currency:
            raise ValueError("a Ruling with an amount must state its currency")
        if self.calculation is None:
            raise ValueError("a Ruling with an amount must show its calculation")
        if self.amount != self.calculation.result:
            raise ValueError(f"amount {self.amount} does not equal the calculation result {self.calculation.result}")
        return self

    @model_validator(mode="after")
    def _final_ruling_has_confidence(self):
        if self.status is RulingStatus.FINAL and self.confidence is None:
            raise ValueError("a final Ruling must carry its calculated confidence")
        return self

    @model_validator(mode="after")
    def _policy_gap_means_unclear_fit(self):
        if self.policy_gap and self.policy_fit is not PolicyFit.UNCLEAR:
            raise ValueError("a Ruling that names a policy_gap must have policy_fit 'unclear'")
        return self


class Precedent(Contract):
    precedent_id: Text
    case_summary: Text
    ruling: Ruling
    source: PrecedentSource
    override_reason: str | None = None
    category: DisputeCategory
    similarity_tags: list[str] = []

    @model_validator(mode="after")
    def _override_has_a_reason(self):
        if self.source is PrecedentSource.HUMAN_OVERRIDE and not self.override_reason:
            raise ValueError("a Precedent from a human_override must carry its override_reason")
        return self


# --- Outcome, review, log ----------------------------------------------------


class Outcome(Contract):
    party: Party
    ruling_summary: Text
    action_status: ActionStatus


class ReviewRecord(Contract):
    reviewer: Text
    decision: ReviewDecision
    reason: str | None = None
    decided_at: datetime

    @model_validator(mode="after")
    def _override_has_a_reason(self):
        if self.decision is ReviewDecision.OVERRIDE and not self.reason:
            raise ValueError("an override must record its reason")
        return self


class LogEvent(Contract):
    case_id: Text
    timestamp: datetime
    agent: Text
    kind: LogEventKind
    summary: Text
    references: list[str] = []  # IDs of items, clauses, submissions


# --- Case --------------------------------------------------------------------


class Case(Contract):
    """The system record built around one Dispute. Its Communication Log is read from the Case store."""

    case_id: Text
    dispute: Dispute
    status: CaseStatus = CaseStatus.FILED
    priority: int = 0  # review-queue order (contract-decisions item 9): 0 unprioritised (routing off), higher is more urgent; Safety Incidents score highest
    priority_reason: str | None = None
    switches: Switches = Switches()
    report_version: str | None = None  # set when the Case is created from the filed report
    evidence: list[EvidenceItem] = []
    evidence_version: str | None = None  # set when the evidence set is sealed
    superseded_evidence_versions: list[str] = []  # earlier versions, oldest first, once the evidence is resealed
    policy_clauses: list[PolicyClause] = []
    policy_version: str | None = None  # the one version every served Policy Clause shares
    precedents: list[Precedent] = []
    submissions: list[Submission] = []
    ruling: Ruling | None = None
    # Built on a superseded evidence version (ticket 18): kept for the record, never argued from or acted on.
    stale_submissions: list[Submission] = []
    stale_ruling: Ruling | None = None
    outcomes: list[Outcome] = []
    review_record: ReviewRecord | None = None
    created_at: datetime
    updated_at: datetime

    @property
    def versions(self) -> dict[str, str | None]:
        """The report, evidence and policy versions in force, under the names a Submission records them by."""
        return {
            "report_version": self.report_version,
            "evidence_version": self.evidence_version,
            "policy_version": self.policy_version,
        }

    @model_validator(mode="after")
    def _one_submission_per_advocate(self):
        authors = [s.author for s in self.submissions]
        for author in set(authors):
            if authors.count(author) > 1:
                raise ValueError(f"a Case holds at most one Submission per advocate; got two from {author.value}")
        return self


# --- Rules enforced in code, not by prompt -----------------------------------
# Rule 3 (amount equals the shown calculation) is a Ruling validator above; the
# recomputation from fare Evidence Items belongs to the Judge's code.


def citation_errors(
    document: Submission | Ruling,
    evidence: list[EvidenceItem],
    policy_clauses: list[PolicyClause],
    precedents: Sequence[Precedent] = (),
) -> list[str]:
    """Check a Submission or Ruling against the sealed evidence set and policy.

    Rule 1: every cited ID must exist. Rule 2: a `missing` item may be cited
    only as missing, never as fact. An argument assessed as unproven may turn
    on a missing item, because the gap is the reason it is unproven.
    Returns one sentence per problem, written so it can be fed back to the
    agent that must fix it; empty means clean.
    """
    status_by_id = {item.evidence_id: item.status for item in evidence}
    clause_ids = {clause.clause_id for clause in policy_clauses}
    precedent_ids = {precedent.precedent_id for precedent in precedents}

    may_be_missing: list[str] = []
    if isinstance(document, Submission):
        as_fact = list(document.facts_relied_on)
        cited_clauses = document.policy_clause_ids
        cited_precedents: list[str] = []
    else:
        as_fact = list(document.cited_evidence_ids)
        if document.calculation:
            as_fact += document.calculation.input_evidence_ids
        for assessment in document.argument_assessments:
            if assessment.verdict is ArgumentVerdict.UNPROVEN:
                may_be_missing += assessment.evidence_ids
            else:
                as_fact += assessment.evidence_ids
        for part in [*document.own_findings, *document.material_evidence]:
            as_fact += part.evidence_ids
        cited_clauses = document.cited_policy_clause_ids
        cited_precedents = document.cited_precedent_ids

    errors = []
    for evidence_id in dict.fromkeys(may_be_missing):
        if evidence_id not in status_by_id:
            errors.append(f"Evidence Item {evidence_id} is cited but is not in the sealed evidence set.")
    for evidence_id in dict.fromkeys(as_fact):
        if evidence_id not in status_by_id:
            errors.append(f"Evidence Item {evidence_id} is cited but is not in the sealed evidence set.")
        elif status_by_id[evidence_id] is EvidenceStatus.MISSING:
            errors.append(
                f"Evidence Item {evidence_id} is marked missing, so it cannot be relied on as fact; "
                "cite it only in missing_evidence_ids."
            )
    for evidence_id in dict.fromkeys(document.missing_evidence_ids):
        if evidence_id not in status_by_id:
            errors.append(f"Evidence Item {evidence_id} is cited as missing but is not in the sealed evidence set.")
        elif status_by_id[evidence_id] is not EvidenceStatus.MISSING:
            errors.append(f"Evidence Item {evidence_id} is cited as missing but its status is {status_by_id[evidence_id].value}.")
    for clause_id in dict.fromkeys(cited_clauses):
        if clause_id not in clause_ids:
            errors.append(f"Policy Clause {clause_id} is cited but is not in the policy given for this Case.")
    for precedent_id in dict.fromkeys(cited_precedents):
        if precedent_id not in precedent_ids:
            errors.append(f"Precedent {precedent_id} is cited but was not given for this Case.")
    return errors
