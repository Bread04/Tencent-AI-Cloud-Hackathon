"""The Case store: the one shared state every agent reads and writes.

In-memory. Every write goes through `_write`, which validates the changed
Case and appends exactly one Log event, so the Communication Log cannot drift
from the state. A refused write changes nothing and logs nothing.
Reads return copies: the only way to change a Case is a store operation.

Not here yet (added by the tickets that need them): escalation, review
decisions, closing a Case, precedents.
"""

from collections.abc import Callable
from datetime import datetime, timezone

from src.config import CONFIG
from src.contracts import (
    ActionStatus,
    Case,
    CaseStatus,
    Dispute,
    EvidenceItem,
    LogEvent,
    LogEventKind,
    Outcome,
    Party,
    PolicyClause,
    Ruling,
    RulingStatus,
    Submission,
    Switches,
)


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

    # --- Reads ---------------------------------------------------------------

    def get_case(self, case_id: str) -> Case:
        return self._case(case_id).model_copy(deep=True)

    def list_cases(self) -> list[Case]:
        return [case.model_copy(deep=True) for case in self._cases.values()]

    def log(self, case_id: str) -> list[LogEvent]:
        """The Communication Log for one Case, oldest first."""
        self._case(case_id)
        return list(self._logs[case_id])

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
        self._cases[case.case_id] = case
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
        self._write(case_id, agent, LogEventKind.CASE_REJECTED, f"Dispute rejected: {reason}", status=CaseStatus.REJECTED)

    def set_priority(self, case_id: str, priority: int, reason: str, agent: str = "intake") -> None:
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
        missing = sum(item.status == "missing" for item in items)
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
        self._write(
            case_id,
            agent,
            LogEventKind.POLICY_RETRIEVED,
            f"{len(clauses)} applicable Policy Clause(s) retrieved.",
            references=[clause.clause_id for clause in clauses],
            policy_clauses=[*case.policy_clauses, *clauses],
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
        """Store the Ruling. A final Ruling moves the Case to `ruled`; a proposal leaves the status alone."""
        case = self._case(case_id)
        amount = f" {ruling.currency} {ruling.amount}" if ruling.amount is not None else ""
        self._write(
            case_id,
            agent,
            LogEventKind.RULING_DRAFTED,
            f"Ruling ({ruling.status.value}): {ruling.outcome.value}, {ruling.remedy.value}{amount}.",
            references=[*ruling.cited_evidence_ids, *ruling.cited_policy_clause_ids, *ruling.cited_precedent_ids],
            status=CaseStatus.RULED if ruling.status is RulingStatus.FINAL else case.status,
            ruling=ruling,
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

    def _write(
        self, case_id: str, agent: str, kind: LogEventKind, summary: str, references: list[str] | None = None, **changes
    ) -> None:
        """Apply `changes` to the Case and append exactly one Log event. Validates before changing anything."""
        now = self._clock()
        case = Case.model_validate({**dict(self._case(case_id)), **changes, "updated_at": now})
        event = LogEvent(
            case_id=case_id, timestamp=now, agent=agent, kind=kind, summary=summary, references=references or []
        )
        self._cases[case_id] = case
        self._logs[case_id].append(event)
