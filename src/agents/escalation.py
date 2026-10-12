"""The Escalation Protocol (architecture.md section 5.7): code decides whether a Ruling may be finalized.

A Ruling that should not be finalized automatically stays a proposal for a Human Reviewer, with the reason
recorded as a Review Trigger. Escalation sits behind a switch: with it off every Ruling is finalized, as in
Tier 0. Further down: the review package a reviewer sees, and the reviewer's decision (confirm, or override
with a recorded reason), after which both parties get the final Outcome.
"""

from datetime import datetime, timezone

from src.agents.judge.numbers import amount_for
from src.agents.outcomes import outcomes_for
from src.agents.policy import ALLOWED_REMEDIES
from src.config import CONFIG
from src.contracts import (
    BalanceOfEvidence,
    Case,
    CaseStatus,
    Contract,
    Dispute,
    DisputeCategory,
    EvidenceStatus,
    Remedy,
    EvidenceItem,
    LogEvent,
    LogEventKind,
    PolicyClause,
    ReviewDecision,
    ReviewRecord,
    ReviewTrigger,
    ReviewTriggerRecord,
    Ruling,
    RulingOutcome,
    RulingStatus,
    Submission,
)
from src.store import CaseStore


def apply_escalation(ruling: Ruling, *, enabled: bool, threshold: float, safety_incident: bool = False) -> Ruling:
    """Hold a Ruling for review when its Confidence is below `threshold`; finalize everything when escalation is off.

    Run after the History step, so a Ruling that History pulls below the threshold is held too.
    Other triggers (balanced evidence, a Policy Gap, a History rule) are added where they arise and already
    leave the Ruling a proposal; this adds the Confidence and amount ones and does not repeat them.
    A Safety Incident is always held, whatever the Confidence and even with escalation off: it is never finalized by code.
    """
    if not enabled and not safety_incident:
        return ruling.model_copy(update={"status": RulingStatus.FINAL})
    triggers = list(ruling.review_triggers)
    held_for = {record.trigger for record in triggers}
    if safety_incident and ReviewTrigger.SAFETY_INCIDENT not in held_for:
        triggers.append(
            ReviewTriggerRecord(
                trigger=ReviewTrigger.SAFETY_INCIDENT,
                reason="This is a Safety Incident, so it is always reviewed by a person, whatever the Confidence.",
            )
        )
    if enabled:
        # Rounded, so floating-point noise (0.7000000000000001) cannot decide a Case at exactly the threshold.
        if ruling.confidence is not None and round(ruling.confidence.value, 2) < threshold and ReviewTrigger.LOW_CONFIDENCE not in held_for:
            triggers.append(
                ReviewTriggerRecord(
                    trigger=ReviewTrigger.LOW_CONFIDENCE,
                    reason=f"Calculated confidence {ruling.confidence.value} is below the configured threshold {threshold}.",
                )
            )
        limit = CONFIG.escalation.amount_limit
        if ruling.amount is not None and ruling.amount > limit and ReviewTrigger.AMOUNT_OVER_LIMIT not in held_for:
            triggers.append(
                ReviewTriggerRecord(
                    trigger=ReviewTrigger.AMOUNT_OVER_LIMIT,
                    reason=f"The amount {ruling.currency} {ruling.amount} is above the configured limit {limit}.",
                )
            )
    return ruling.model_copy(update={"status": RulingStatus.PROPOSAL if triggers else ruling.status, "review_triggers": triggers})


# --- The review package -------------------------------------------------------------------------------------------


class ReviewPackage(Contract):
    """Everything a Human Reviewer needs to decide a held Case."""

    case_id: str
    dispute: Dispute
    reasons: list[ReviewTriggerRecord]
    proposed_ruling: Ruling | None  # None when a stage failed before any Ruling existed
    submissions: list[Submission]
    evidence: list[EvidenceItem]
    policy_clauses: list[PolicyClause]


def review_package(case: Case, log: list[LogEvent]) -> ReviewPackage:
    return ReviewPackage(
        case_id=case.case_id,
        dispute=case.dispute,
        reasons=_reasons(case, log),
        proposed_ruling=case.ruling,
        submissions=case.submissions,
        evidence=case.evidence,
        policy_clauses=case.policy_clauses,
    )


def _reasons(case: Case, log: list[LogEvent]) -> list[ReviewTriggerRecord]:
    if case.ruling is not None and case.ruling.review_triggers:
        return case.ruling.review_triggers
    held = [event for event in log if event.kind is LogEventKind.ESCALATED]
    if not held:
        return []
    event = held[-1]  # no Ruling: the reason is only in the log, written when the Case was held
    reason = event.summary.removeprefix("Sent to a Human Reviewer: ")
    trigger = next((ReviewTrigger(ref) for ref in event.references if ref in ReviewTrigger._value2member_map_), ReviewTrigger.STAGE_FAILED)
    return [ReviewTriggerRecord(trigger=trigger, reason=reason)]


# --- The reviewer's decision --------------------------------------------------------------------------------------


class ReviewError(Exception):
    """A decision that cannot be made, with the reason."""


class ReviewNotPossible(ReviewError):
    """The Case is not in a state to be decided (not pending review, or no proposed Ruling)."""


class ReviewInvalid(ReviewError):
    """The decision itself is incomplete: a missing reviewer name or a missing override reason."""


def decide_review(store: CaseStore, case_id: str, *, reviewer: str, decision: ReviewDecision, reason: str | None = None) -> Case:
    """Confirm the proposed Ruling, or override it with a reason; then both parties get the final Outcome."""
    case = store.get_case(case_id)
    if case.status is not CaseStatus.PENDING_REVIEW:
        raise ReviewNotPossible(f"{case_id} is not pending review (it is {case.status.value}).")
    if case.ruling is None:
        raise ReviewNotPossible(f"{case_id} has no proposed Ruling to confirm or override, because a stage failed before one was made.")
    if not reviewer.strip():
        raise ReviewInvalid("A reviewer name is required.")
    if decision is ReviewDecision.OVERRIDE and not (reason or "").strip():
        raise ReviewInvalid("An override needs a reason.")

    final = (_route_decision(case, decision, reviewer.strip(), (reason or "").strip())
             if case.dispute.category is DisputeCategory.ROUTE_DEVIATION
             else _confirmed(case.ruling) if decision is ReviewDecision.CONFIRM
             else _overridden(case, reviewer.strip(), reason.strip()))
    record = ReviewRecord(reviewer=reviewer.strip(), decision=decision, reason=(reason or "").strip() or None, decided_at=datetime.now(timezone.utc))
    store.finish_review(case_id, record, final, outcomes_for(final, case))  # one write: the Case is never ruled with nobody told
    return store.get_case(case_id)


def _confirmed(ruling: Ruling) -> Ruling:
    return ruling.model_copy(update={"status": RulingStatus.FINAL})


def _overridden(case: Case, reviewer: str, reason: str) -> Ruling:
    """The other outcome. The category is binary, so the Remedy is the one its policy allows and the amount is recomputed."""
    proposed = case.ruling
    outcome = RulingOutcome.REJECT if proposed.outcome is RulingOutcome.UPHOLD else RulingOutcome.UPHOLD
    remedy = ALLOWED_REMEDIES[case.dispute.category][outcome]
    fare = next(item.evidence_id for item in case.evidence if item.source == "fare")
    amount, calculation = amount_for(case, remedy, [fare])
    return proposed.model_copy(
        update={
            "status": RulingStatus.FINAL,
            "outcome": outcome,
            "remedy": remedy,
            "balance_of_evidence": BalanceOfEvidence.CLAIMANT if outcome is RulingOutcome.UPHOLD else BalanceOfEvidence.RESPONDENT,
            "amount": amount,
            "currency": CONFIG.currency if amount is not None else None,
            "calculation": calculation,
            "reasoning_summary": f"Overridden by {reviewer}: {reason} The proposal was to {proposed.outcome.value}: {proposed.reasoning_summary}",
        }
    )


def _route_decision(case: Case, decision: ReviewDecision, reviewer: str, reason: str) -> Ruling:
    """Keep Route Deviation's three outcomes and recompute any approved refund."""
    proposed = case.ruling
    outcome, remedy = proposed.outcome, proposed.remedy
    amount = calculation = None
    if decision is ReviewDecision.OVERRIDE:
        if outcome in (RulingOutcome.UPHOLD, RulingOutcome.PARTIALLY_UPHOLD):
            outcome, remedy = RulingOutcome.REJECT, Remedy.NO_ACTION
        else:
            remedy = Remedy.PARTIAL_REFUND  # refined below from the code-computed amount
    if remedy in (Remedy.FULL_REFUND, Remedy.PARTIAL_REFUND):
        by_source = {item.source: item for item in case.evidence}
        inputs = [by_source.get("route"), by_source.get("fare")]
        if any(item is None or item.status is not EvidenceStatus.AVAILABLE or not item.derived.get("available") for item in inputs):
            raise ReviewInvalid("A route refund requires available route and fare evidence; the case remains pending.")
        try:
            amount, calculation = amount_for(case, remedy, [item.evidence_id for item in inputs])
            from src.tools.evidence.route import analyze_fare
            from decimal import Decimal
            paid = Decimal(analyze_fare(inputs[1].content, inputs[0].derived)["paid_net"])
        except (ValueError, KeyError, StopIteration, ArithmeticError) as error:
            raise ReviewInvalid("Route refund inputs cannot be reconciled; the case remains pending.") from error
        if amount is None or amount <= 0:
            raise ReviewInvalid("The code-computed route refund must be positive; the case remains pending.")
        expected_remedy = Remedy.FULL_REFUND if amount == paid else Remedy.PARTIAL_REFUND
        expected_outcome = RulingOutcome.UPHOLD if amount == paid else RulingOutcome.PARTIALLY_UPHOLD
        if decision is ReviewDecision.CONFIRM and (remedy is not expected_remedy or outcome is not expected_outcome):
            raise ReviewInvalid("The proposed remedy does not match the code-computed refund.")
        outcome, remedy = expected_outcome, expected_remedy
    return proposed.model_copy(update={
        "status": RulingStatus.FINAL, "outcome": outcome, "remedy": remedy,
        "amount": amount, "currency": CONFIG.currency if amount is not None else None,
        "calculation": calculation,
        "balance_of_evidence": (BalanceOfEvidence.CLAIMANT if outcome in (RulingOutcome.UPHOLD, RulingOutcome.PARTIALLY_UPHOLD)
                                else proposed.balance_of_evidence if decision is ReviewDecision.CONFIRM else BalanceOfEvidence.RESPONDENT),
        "reasoning_summary": proposed.reasoning_summary if decision is ReviewDecision.CONFIRM else
            f"Overridden by {reviewer}: {reason} The proposal was to {proposed.outcome.value}: {proposed.reasoning_summary}",
    })
