"""The Case store: the one shared state every agent reads and writes.

In-memory. Every write goes through `_write`, which validates the changed
Case and appends exactly one Log event, so the Communication Log cannot drift
from the state. A refused write changes nothing and logs nothing.
Writes and reads both copy: the only way to change a Case is a store operation.
A rejected or closed Case accepts no further writes.

Not here yet (added by the tickets that need them): escalation, review
decisions, closing a Case, precedents.
"""

import threading
from collections.abc import Callable
from datetime import datetime, timezone

from src.config import CONFIG
from src.contracts import (
    ActionStatus,
    Case,
    CaseStatus,
    Dispute,
    EvidenceItem,
    EvidenceStatus,
    LogEvent,
    LogEventKind,
    Outcome,
    Party,
    ReviewDecision,
    ReviewRecord,
    PolicyClause,
    Precedent,
    ReviewTriggerRecord,
    Ruling,
    RulingStatus,
    Submission,
    Switches,
)
from src.llm.calls import ModelCall


class StoreError(Exception):
    """A write the store refuses, with the reason."""


class CaseNotFound(StoreError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CaseStore:
    def __init__(self, clock: Callable[[], datetime] = _utc_now):
        self._clock = clock
        self._cases: dict[str, Case] = {}
        self._logs: dict[str, list[LogEvent]] = {}
        self._calls: dict[str, list[ModelCall]] = {}  # the model calls behind each Case, for the console
        self._lock = threading.RLock()  # the two advocates write from separate threads

    # --- Reads ---------------------------------------------------------------

    def get_case(self, case_id: str) -> Case:
        return self._case(case_id).model_copy(deep=True)

    def list_cases(self) -> list[Case]:
        return [case.model_copy(deep=True) for case in self._cases.values()]

    def log(self, case_id: str) -> list[LogEvent]:
        """The Communication Log for one Case, oldest first."""
        self._case(case_id)
        return [event.model_copy(deep=True) for event in self._logs[case_id]]

    def calls(self, case_id: str) -> list[ModelCall]:
        """The model calls made for one Case, in order."""
        self._case(case_id)
        return list(self._calls.get(case_id, []))

    # --- Writes --------------------------------------------------------------

    def create_case(self, dispute: Dispute, switches: Switches | None = None, agent: str = "intake") -> Case:
        now = self._clock()
        case = Case(
            case_id=f"CASE-{len(self._cases) + 1:04d}",
            dispute=dispute,
            switches=switches or CONFIG.switches,
            created_at=now,
            updated_at=now,
        )
        self._cases[case.case_id] = case.model_copy(deep=True)
        self._logs[case.case_id] = [
            LogEvent(
                case_id=case.case_id,
                timestamp=now,
                agent=agent,
                kind=LogEventKind.CASE_FILED,
                summary=f"{dispute.claimant.value.capitalize()} filed a {dispute.category.value} Dispute on trip {dispute.trip_id}.",
                references=[dispute.dispute_id, dispute.trip_id],
            )
        ]
        return case.model_copy(deep=True)

    def reject_case(self, case_id: str, reason: str, agent: str = "intake") -> None:
        self._require_status(case_id, CaseStatus.FILED, "rejected")
        self._write(case_id, agent, LogEventKind.CASE_REJECTED, f"Dispute rejected: {reason}", status=CaseStatus.REJECTED)

    def set_priority(self, case_id: str, priority: int, reason: str, agent: str = "intake") -> None:
        self._require_status(case_id, CaseStatus.FILED, "given a priority")
        self._write(
            case_id,
            agent,
            LogEventKind.PRIORITY_SET,
            f"Priority set to {priority}: {reason}",
            status=CaseStatus.PRIORITISED,
            priority=priority,
            priority_reason=reason,
        )

    def add_evidence(self, case_id: str, items: list[EvidenceItem], agent: str) -> None:
        case = self._case(case_id)
        if case.evidence_version is not None:
            raise StoreError(f"Evidence for {case_id} is sealed as {case.evidence_version}; nothing can be added.")
        new_ids = [item.evidence_id for item in items]
        known_ids = {item.evidence_id for item in case.evidence}
        duplicates = [i for n, i in enumerate(new_ids) if i in known_ids or i in new_ids[:n]]
        if duplicates:
            raise StoreError(f"Evidence Item IDs must be unique in a Case; already present: {', '.join(duplicates)}.")
        missing = sum(item.status is EvidenceStatus.MISSING for item in items)
        self._write(
            case_id,
            agent,
            LogEventKind.EVIDENCE_RETURNED,
            f"{len(items)} Evidence Item(s) returned, {missing} marked missing.",
            references=new_ids,
            status=CaseStatus.GATHERING_EVIDENCE,
            evidence=[*case.evidence, *items],
        )

    def seal_evidence(self, case_id: str, agent: str = "orchestrator") -> str:
        """Freeze the evidence set and return its version ID."""
        case = self._case(case_id)
        if case.evidence_version is not None:
            raise StoreError(f"Evidence for {case_id} is already sealed as {case.evidence_version}.")
        version = f"{case_id}-evidence-v1"
        self._write(
            case_id,
            agent,
            LogEventKind.EVIDENCE_SEALED,
            f"Evidence set sealed as {version} with {len(case.evidence)} item(s).",
            references=[version],
            status=CaseStatus.BUILDING_CASES,
            evidence_version=version,
        )
        return version

    def add_policy_clauses(self, case_id: str, clauses: list[PolicyClause], agent: str) -> None:
        case = self._case(case_id)
        new_ids = [clause.clause_id for clause in clauses]
        known_ids = {clause.clause_id for clause in case.policy_clauses}
        duplicates = [i for n, i in enumerate(new_ids) if i in known_ids or i in new_ids[:n]]
        if duplicates:
            raise StoreError(f"Policy Clause IDs must be unique in a Case; already present: {', '.join(duplicates)}.")
        self._write(
            case_id,
            agent,
            LogEventKind.POLICY_RETRIEVED,
            f"{len(clauses)} applicable Policy Clause(s) retrieved.",
            references=new_ids,
            policy_clauses=[*case.policy_clauses, *clauses],
        )

    def add_precedents(self, case_id: str, precedents: list[Precedent], summary: str, agent: str = "policy") -> None:
        """Serve the similar past Rulings found for this Case, once; the summary says how they were chosen."""
        case = self._case(case_id)
        if case.precedents:
            raise StoreError(f"{case_id} already has its Precedents.")
        self._write(
            case_id, agent, LogEventKind.PRECEDENT_RETRIEVED, summary,
            references=[p.precedent_id for p in precedents], precedents=precedents,
        )

    def add_submission(self, case_id: str, submission: Submission) -> None:
        case = self._case(case_id)
        if case.evidence_version is None:
            raise StoreError(f"A Submission cannot be filed for {case_id} until its evidence is sealed.")
        submissions = [*case.submissions, submission]
        self._write(
            case_id,
            submission.author.value,
            LogEventKind.SUBMISSION_FILED,
            f"Submission filed: {submission.requested_outcome}",
            references=[*submission.facts_relied_on, *submission.policy_clause_ids],
            status=CaseStatus.JUDGING if len(submissions) == 2 else case.status,
            submissions=submissions,
        )

    def set_ruling(self, case_id: str, ruling: Ruling, agent: str = "judge") -> None:
        """Final rulings become `ruled`; triggered proposals become `pending_review`."""
        case = self._case(case_id)
        if len(case.submissions) != 2:
            raise StoreError(f"A Ruling cannot be stored for {case_id} until both Submissions are filed.")
        amount = f" {ruling.currency} {ruling.amount}" if ruling.amount is not None else ""
        if ruling.status is RulingStatus.PROPOSAL:
            reasons = "; ".join(f"{record.trigger.value}: {record.reason}" for record in ruling.review_triggers)
            summary = "Proposal recorded: no final decision or payment authorization."
            if reasons:
                summary += f" Pending review: {reasons}"
            status = CaseStatus.PENDING_REVIEW if ruling.review_triggers else case.status
        else:
            summary = f"Ruling ({ruling.status.value}): {ruling.outcome.value}, {ruling.remedy.value}{amount}."
            status = CaseStatus.RULED
        self._write(
            case_id,
            agent,
            LogEventKind.RULING_DRAFTED,
            summary,
            references=[*ruling.cited_evidence_ids, *ruling.cited_policy_clause_ids, *ruling.cited_precedent_ids],
            status=status,
            ruling=ruling,
        )

    def mark_pending_review(self, case_id: str, triggers: list[ReviewTriggerRecord], agent: str = "escalation") -> None:
        """Hold the Case for a Human Reviewer and say why. The review queue and reviewer screen come with escalation (ticket 09)."""
        reasons = "; ".join(record.reason for record in triggers)
        self._write(
            case_id,
            agent,
            LogEventKind.ESCALATED,
            f"Sent to a Human Reviewer: {reasons}",
            references=[record.trigger.value for record in triggers],
            status=CaseStatus.PENDING_REVIEW,
        )

    def finish_review(self, case_id: str, record: ReviewRecord, ruling: Ruling, outcomes: list[Outcome], agent: str = "escalation") -> None:
        """Record a Human Reviewer's decision in one write: the final Ruling replaces the proposal and the parties' final Outcomes replace the pending ones."""
        self._require_status(case_id, CaseStatus.PENDING_REVIEW, "reviewed")
        verb = "confirmed" if record.decision is ReviewDecision.CONFIRM else "overrode"
        why = f" Reason: {record.reason}" if record.reason else ""
        told = {o.party for o in outcomes if o.action_status is not ActionStatus.PENDING_REVIEW}
        self._write(
            case_id,
            agent,
            LogEventKind.REVIEW_DECISION,
            f"{record.reviewer} {verb} the proposed Ruling ({ruling.outcome.value}, {ruling.remedy.value}).{why}",
            status=CaseStatus.NOTIFIED if told == set(Party) else CaseStatus.RULED,
            ruling=ruling,
            review_record=record,
            outcomes=outcomes,
        )

    def add_outcome(self, case_id: str, outcome: Outcome, agent: str = "orchestrator") -> None:
        """Record what one party is told. Once both parties have a decided Outcome on a ruled Case, it is `notified`."""
        case = self._case(case_id)
        outcomes = [*case.outcomes, outcome]
        told = {o.party for o in outcomes if o.action_status is not ActionStatus.PENDING_REVIEW}
        notified = case.status is CaseStatus.RULED and told == set(Party)
        self._write(
            case_id,
            agent,
            LogEventKind.OUTCOME_SENT,
            f"Outcome sent to the {outcome.party.value} ({outcome.action_status.value}).",
            status=CaseStatus.NOTIFIED if notified else case.status,
            outcomes=outcomes,
        )

    def record_call(self, case_id: str, call: ModelCall) -> None:
        """Keep one model call and log it as a single `model_call` row."""
        with self._lock:
            self._calls.setdefault(case_id, []).append(call)
            retry = f"; sent back because: {call.sent_back_because[:160]}" if call.sent_back_because else ""
            what = {
                "ok": f"replied in {call.seconds:.1f}s",
                "invalid": f"replied with the wrong shape after {call.seconds:.1f}s",
                "failed": f"failed after {call.seconds:.1f}s: {(call.problem or '')[:120]}",
            }[call.outcome]
            self._write(case_id, call.agent, LogEventKind.MODEL_CALL, f"Call {call.attempt} on {call.model} {what}{retry}")

    def log_event(
        self, case_id: str, agent: str, kind: LogEventKind, summary: str, references: list[str] | None = None
    ) -> None:
        """Log something that happened without changing the Case, such as an evidence request."""
        self._write(case_id, agent, kind, summary, references=references or [])

    # --- Internals -----------------------------------------------------------

    def _case(self, case_id: str) -> Case:
        if case_id not in self._cases:
            raise CaseNotFound(f"No Case with ID {case_id}.")
        return self._cases[case_id]

    def _require_status(self, case_id: str, required: CaseStatus, action: str) -> None:
        status = self._case(case_id).status
        if status is not required:
            raise StoreError(f"{case_id} can only be {action} while it is {required.value}; it is {status.value}.")

    def _write(
        self, case_id: str, agent: str, kind: LogEventKind, summary: str, references: list[str] | None = None, **changes
    ) -> None:
        """Apply `changes` to the Case and append exactly one Log event. Validates before changing anything."""
        with self._lock:
            self._apply(case_id, agent, kind, summary, references, changes)

    def _apply(self, case_id, agent, kind, summary, references, changes) -> None:
        current = self._case(case_id)
        if changes and current.status in (CaseStatus.REJECTED, CaseStatus.CLOSED):
            raise StoreError(f"{case_id} is {current.status.value}; it accepts no further writes.")
        now = self._clock()
        # Deep copy so the caller's objects and the stored Case never share state.
        case = Case.model_validate({**dict(current), **changes, "updated_at": now}).model_copy(deep=True)
        event = LogEvent(
            case_id=case_id, timestamp=now, agent=agent, kind=kind, summary=summary, references=references or []
        )
        self._cases[case_id] = case
        self._logs[case_id].append(event)
