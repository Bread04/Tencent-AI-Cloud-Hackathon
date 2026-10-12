"""The orchestrator: ordinary code that runs one Dispute through its stages in order.

No model chooses the next step (architecture.md section 3.2). Tracer-bullet
version: intake, evidence, policy, both advocates (in parallel), the Judge, the History step and
Outcomes. A proposal or a failed Judge holds the Case for review. Not here yet: priority,
supporting agents and their switches, the review queue and reviewer (ticket 09).
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

from src.agents.advocates import build_submission
from src.agents.escalation import apply_escalation
from src.agents.image_analysis import analyse_photos
from src.agents.evidence_agents import gather_evidence_safely, run_evidence_agent
from src.agents.judge import judge
from src.agents.judge.history import apply_history
from src.agents.outcomes import outcomes_for, pending_outcomes
from src.agents.policy import policy_for
from src.agents.routing import score
from src.agents.policy.precedents import describe, load_embedder, retrieve_precedents, seeded_precedents
from src.config import CONFIG
from src.contracts import (
    Advocate,
    Case,
    Dispute,
    DisputeCategory,
    EvidenceStatus,
    LogEventKind,
    Party,
    Precedent,
    ReviewTrigger,
    ReviewTriggerRecord,
    RulingStatus,
    Submission,
    Switches,
)
from src.intake import Catalog, UnknownTrip
from src.llm.adapter import ModelAdapter, ModelError
from src.llm.recording import RecordingModel
from src.llm.repair import StageFailed
from src.store import CaseStore
from src.tools.evidence import gather_evidence

SUPPORTED_CATEGORIES = frozenset({DisputeCategory.NO_SHOW_CHARGE, DisputeCategory.ROUTE_DEVIATION})
ROUTED_CATEGORIES = SUPPORTED_CATEGORIES | {DisputeCategory.SAFETY_INCIDENT}


def run_dispute(
    dispute: Dispute, *, store: CaseStore, model: ModelAdapter, catalog: Catalog,
    switches: Switches | None = None, precedents: Sequence[Precedent] | None = None,
) -> Case:
    case = store.create_case(dispute, switches)
    case_id = case.case_id
    if not isinstance(model, RecordingModel):
        model = RecordingModel(model, store)  # every model call is recorded and shown in the log

    reason = _rejection_reason(dispute, catalog, case.switches.sla_routing)
    if reason:
        store.reject_case(case_id, reason)
        return store.get_case(case_id)

    if case.switches.sla_routing:  # a Priority and its reason for every Case; without the switch all Cases share one
        record = catalog.trip(dispute.trip_id)
        charged = record["receipt"]["paid_net"] if dispute.category is DisputeCategory.ROUTE_DEVIATION else record["trip"]["cancellation_fee"]
        priority = score(dispute, Decimal(charged))
        store.set_priority(case_id, priority.value, priority.reason)

    store.log_event(
        case_id,
        "orchestrator",
        LogEventKind.EVIDENCE_REQUESTED,
        f"Requested GPS, chat, fare and History evidence for trip {dispute.trip_id}.",
        references=[dispute.trip_id],
    )
    if case.switches.evidence_agents:  # the tools run first, then each side's agent reads the party text, all before sealing
        store.add_evidence(case_id, gather_evidence_safely(dispute.trip_id, catalog), agent="evidence")
        for party in Party:
            store.add_evidence(case_id, run_evidence_agent(party, store.get_case(case_id), model), agent=f"{party.value}_evidence")
    else:
        store.add_evidence(case_id, gather_evidence(dispute.trip_id, catalog), agent="evidence")
    if case.switches.image_analysis and dispute.photos:  # findings join the evidence before it is sealed; with the switch off photos are only stored
        trip = catalog.trip(dispute.trip_id)["trip"]
        window = (datetime.fromisoformat(trip["scheduled_time"]), datetime.fromisoformat(trip["cancellation_time"]))
        findings = analyse_photos(store.get_case(case_id), window, model)
        store.add_evidence(case_id, findings, agent="image_analysis")
        for number, photo in enumerate(dispute.photos, start=1):
            mine = [i for i in findings if i.evidence_id.startswith(f"EV-PHOTO-{number}")]
            outcome = "unanalysed" if any(i.status is EvidenceStatus.MISSING for i in mine) else "analysed"
            store.log_event(case_id, "image_analysis", LogEventKind.PHOTO_ANALYSED, f"Photo {photo} {outcome}: {len(mine)} finding(s).", references=[i.evidence_id for i in mine])
    store.seal_evidence(case_id)
    store.add_policy_clauses(case_id, policy_for(dispute.category), agent="policy")
    if case.switches.policy_precedent:  # the same Precedents go to both advocates and the Judge; advisory only
        mode = CONFIG.precedents.retrieval
        found = retrieve_precedents(
            store.get_case(case_id), seeded_precedents() if precedents is None else precedents,
            mode=mode, embedder=load_embedder() if mode == "embeddings" else None,
        )
        store.add_precedents(case_id, [s.precedent for s in found.served], describe(found))

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
            record=lambda kind, summary, references=None: store.log_event(case_id, "judge", kind, summary, references),
        )
    except (StageFailed, ModelError) as failure:
        reason = ReviewTriggerRecord(trigger=ReviewTrigger.STAGE_FAILED, reason=_failure_reason("Judge", "Ruling", failure))
        _hold_for_review(store, case_id, [reason], pending_outcomes())
        return store.get_case(case_id)

    # History is applied only now, after the outcome is fixed (ADR 0001).
    ruling = apply_history(ruling, store.get_case(case_id))
    ruling = apply_escalation(ruling, enabled=case.switches.escalation, threshold=CONFIG.escalation.confidence_threshold, safety_incident=dispute.category is DisputeCategory.SAFETY_INCIDENT)
    if dispute.category is DisputeCategory.ROUTE_DEVIATION and ruling.status is RulingStatus.PROPOSAL:
        ruling = ruling.model_copy(update={"amount": None, "currency": None, "calculation": None})
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


def _rejection_reason(dispute: Dispute, catalog: Catalog, routing: bool = False) -> str | None:
    try:
        catalog.trip(dispute.trip_id)
    except UnknownTrip:
        return f"Trip {dispute.trip_id} does not exist."
    supported_now = ROUTED_CATEGORIES if routing else SUPPORTED_CATEGORIES
    if dispute.category not in supported_now:
        supported = ", ".join(sorted(category.value for category in supported_now))
        return f"{dispute.category.value} Disputes cannot be resolved yet; supported: {supported}."
    return None


def _hold_for_review(store: CaseStore, case_id: str, triggers: list[ReviewTriggerRecord], outcomes) -> None:
    store.mark_pending_review(case_id, triggers)
    for outcome in outcomes:
        store.add_outcome(case_id, outcome)
