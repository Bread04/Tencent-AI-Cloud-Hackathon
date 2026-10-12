"""The orchestrator: ordinary code that runs one Dispute through its stages in order.

No model chooses the next step (architecture.md section 3.2). Tracer-bullet
version: intake, evidence, policy, both advocates (in parallel), the Judge, the History step and
Outcomes. A proposal or a failed Judge holds the Case for review. Not here yet: priority,
supporting agents and their switches, the review queue and reviewer (ticket 09).
"""

from concurrent.futures import ThreadPoolExecutor

from src.agents.advocates import build_submission
from src.agents.escalation import apply_escalation
from src.agents.judge import judge
from src.agents.judge.history import apply_history
from src.agents.outcomes import outcomes_for, pending_outcomes
from src.agents.policy import policy_for
from src.config import CONFIG
from src.contracts import (
    Advocate,
    Case,
    Dispute,
    DisputeCategory,
    LogEventKind,
    ReviewTrigger,
    ReviewTriggerRecord,
    RulingStatus,
    Submission,
    Switches,
)
from src.intake import Catalog, UnknownTrip
from src.llm.adapter import ModelAdapter, ModelError
from src.llm.repair import StageFailed
from src.store import CaseStore
from src.tools.evidence import gather_evidence

SUPPORTED_CATEGORIES = frozenset({DisputeCategory.NO_SHOW_CHARGE})


def run_dispute(
    dispute: Dispute, *, store: CaseStore, model: ModelAdapter, catalog: Catalog, switches: Switches | None = None
) -> Case:
    case = store.create_case(dispute, switches)
    case_id = case.case_id

    reason = _rejection_reason(dispute, catalog)
    if reason:
        store.reject_case(case_id, reason)
        return store.get_case(case_id)

    store.log_event(
        case_id,
        "orchestrator",
        LogEventKind.EVIDENCE_REQUESTED,
        f"Requested GPS, chat, fare and History evidence for trip {dispute.trip_id}.",
        references=[dispute.trip_id],
    )
    store.add_evidence(case_id, gather_evidence(dispute.trip_id, catalog), agent="evidence")
    store.seal_evidence(case_id)
    store.add_policy_clauses(case_id, policy_for(dispute.category), agent="policy")

    # Both advocates work from this snapshot (sealed evidence and policy), taken before either has filed.
    sealed = store.get_case(case_id)
    submissions, failures = _build_submissions(sealed, model)
    for submission in submissions.values():
        store.add_submission(case_id, submission)
    if failures:
        reason = ReviewTriggerRecord(trigger=ReviewTrigger.STAGE_FAILED, reason=" ".join(failures))
        _hold_for_review(store, case_id, [reason], pending_outcomes())
        return store.get_case(case_id)

    try:
        ruling = judge(
            store.get_case(case_id),
            submissions[Advocate.RIDER_ADVOCATE],
            submissions[Advocate.DRIVER_ADVOCATE],
            model,
            record=lambda kind, summary: store.log_event(case_id, "judge", kind, summary),
        )
    except (StageFailed, ModelError) as failure:
        reason = ReviewTriggerRecord(trigger=ReviewTrigger.STAGE_FAILED, reason=_failure_reason("Judge", "Ruling", failure))
        _hold_for_review(store, case_id, [reason], pending_outcomes())
        return store.get_case(case_id)

    # History is applied only now, after the outcome is fixed (ADR 0001).
    ruling = apply_history(ruling, store.get_case(case_id))
    ruling = apply_escalation(ruling, enabled=case.switches.escalation, threshold=CONFIG.escalation.confidence_threshold)
    store.set_ruling(case_id, ruling)
    if ruling.status is RulingStatus.PROPOSAL:
        store.mark_pending_review(case_id, ruling.review_triggers)
    for outcome in outcomes_for(ruling, store.get_case(case_id)):
        store.add_outcome(case_id, outcome)
    return store.get_case(case_id)


def _build_submissions(sealed: Case, model: ModelAdapter) -> tuple[dict[Advocate, Submission], list[str]]:
    """Run both advocates at once; neither can see the other, since each reads only the sealed snapshot."""

    def attempt(advocate: Advocate) -> Submission | StageFailed | ModelError:
        try:
            return build_submission(advocate, sealed, model)
        except (StageFailed, ModelError) as failure:  # a dead model is a failed stage, never a crash or an invented reply
            return failure

    with ThreadPoolExecutor(max_workers=len(Advocate)) as pool:
        results = dict(zip(Advocate, pool.map(attempt, Advocate)))
    submissions = {advocate: result for advocate, result in results.items() if isinstance(result, Submission)}
    failures = [
        _failure_reason(advocate.value.replace("_", " "), "Submission", result)
        for advocate, result in results.items()
        if isinstance(result, (StageFailed, ModelError))
    ]
    return submissions, failures


def _failure_reason(subject: str, noun: str, failure: Exception) -> str:
    """Why a stage failed, worded for a person: the model itself failed, or its output stayed invalid."""
    if isinstance(failure, ModelError):
        return f"The {subject} could not run because the model failed: {failure}"
    return f"The {subject} could not produce a valid {noun}: {failure}"


def _rejection_reason(dispute: Dispute, catalog: Catalog) -> str | None:
    try:
        catalog.trip(dispute.trip_id)
    except UnknownTrip:
        return f"Trip {dispute.trip_id} does not exist."
    if dispute.category not in SUPPORTED_CATEGORIES:
        supported = ", ".join(sorted(category.value for category in SUPPORTED_CATEGORIES))
        return f"{dispute.category.value} Disputes cannot be resolved yet; supported: {supported}."
    return None


def _hold_for_review(store: CaseStore, case_id: str, triggers: list[ReviewTriggerRecord], outcomes) -> None:
    store.mark_pending_review(case_id, triggers)
    for outcome in outcomes:
        store.add_outcome(case_id, outcome)
