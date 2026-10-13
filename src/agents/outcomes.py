"""Outcome wording (architecture.md section 5.6): a template, not a model call.

It reads the finished Ruling and writes what each party is told. It cannot
change the substance. An action is only ever `recommended` (or `pending_review`
for a proposal); executing a payment is outside this system.
"""

from src.contracts import ActionStatus, Case, DisputeCategory, Outcome, Party, Ruling, RulingOutcome, RulingStatus


def outcomes_for(ruling: Ruling, case: Case) -> list[Outcome]:
    claimant = case.dispute.claimant
    if ruling.status is RulingStatus.PROPOSAL:
        return pending_outcomes(case)
    return [
        Outcome(party=party, ruling_summary=_route_decision(ruling, claimant, party) if case.dispute.category is DisputeCategory.ROUTE_DEVIATION else _decision(ruling, claimant, party, case.dispute.category), action_status=ActionStatus.RECOMMENDED)
        for party in Party
    ]


def pending_outcomes(case: Case | None = None) -> list[Outcome]:
    """What both parties are told while a person reviews the Case, including when there is no Ruling at all."""
    if case is not None and case.dispute.category is DisputeCategory.SAFETY_INCIDENT:
        return [_pending_safety(party, party is case.dispute.claimant) for party in Party]
    return [_pending(party) for party in Party]


def _pending(party: Party) -> Outcome:
    return Outcome(
        party=party,
        ruling_summary=(
            "Your dispute is under review by a person. A decision is pending, and you will be told the outcome "
            "when the review is complete."
        ),
        action_status=ActionStatus.PENDING_REVIEW,
    )


def _pending_safety(party: Party, filed_it: bool) -> Outcome:
    """ADR 0006: whoever reported is told a Safety Officer has it as a priority; the other party is told only that a report is under review, never what it says."""
    told = (
        "A Safety Officer is reviewing your report as a priority and will follow up with you. Nothing about the fare has been decided yet."
        if filed_it
        else "A report about this trip is under review by a person. You will be told if anything is needed from you."
    )
    return Outcome(party=party, ruling_summary=told, action_status=ActionStatus.PENDING_REVIEW)


def _decision(ruling: Ruling, claimant: Party, reader: Party, category: DisputeCategory) -> str:
    whose = "Your claim" if reader is claimant else f"The {claimant.value}'s claim"
    reason = f" Reason: {ruling.reasoning_summary}"
    if category is DisputeCategory.SAFETY_INCIDENT:
        return _safety_decision(ruling, whose, reason)
    if category is DisputeCategory.PROPERTY_DAMAGE:
        return _damage_decision(ruling, whose, reason)
    if ruling.outcome is RulingOutcome.REJECT:
        return f"{whose} was not upheld. The no-show fee stands.{reason}"
    amount = f"The {ruling.currency} {ruling.amount} no-show fee" if ruling.amount is not None else "The no-show fee"
    reversed_ = "will be reversed" if reader is claimant else "is reversed"
    return f"{whose} was upheld. {amount} {reversed_}.{reason}"


def _damage_decision(ruling: Ruling, whose: str, reason: str) -> str:
    """What a party is told about a cleaning-fee claim. Charging the fee is outside this system; it is recommended."""
    if ruling.outcome is RulingOutcome.REJECT:
        return f"{whose} for a cleaning fee was not upheld. No cleaning fee is recommended.{reason}"
    label = "partly upheld" if ruling.outcome is RulingOutcome.PARTIALLY_UPHOLD else "upheld"
    return f"{whose} was {label}. A cleaning fee of {ruling.currency} {ruling.amount} is recommended, not charged by this system.{reason}"


def _safety_decision(ruling: Ruling, whose: str, reason: str) -> str:
    """What a party is told about a Safety Incident. Conduct is reviewed separately; this is only the outcome of the claim."""
    if ruling.outcome is RulingOutcome.REJECT:
        return f"{whose} was not upheld on the evidence. The report is kept on record.{reason}"
    return f"{whose} was upheld. A full refund of the fare is recommended, and the report goes on record for review.{reason}"


def _route_decision(ruling: Ruling, claimant: Party, reader: Party) -> str:
    whose = "Your claim" if reader is claimant else f"The {claimant.value}'s claim"
    if ruling.outcome is RulingOutcome.REJECT:
        decision = f"{whose} was rejected. No refund is recommended."
    else:
        label = "partially upheld" if ruling.outcome is RulingOutcome.PARTIALLY_UPHOLD else "upheld"
        decision = f"{whose} was {label}. A {ruling.currency} {ruling.amount} route-fare refund is recommended, not executed."
    return f"{decision} Reason: {ruling.reasoning_summary}"
