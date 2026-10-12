"""Outcome wording (architecture.md section 5.6): a template, not a model call.

It reads the finished Ruling and writes what each party is told. It cannot
change the substance. An action is only ever `recommended` (or `pending_review`
for a proposal); executing a payment is outside this system.
"""

from src.contracts import ActionStatus, Case, DisputeCategory, Outcome, Party, Ruling, RulingOutcome, RulingStatus


def outcomes_for(ruling: Ruling, case: Case) -> list[Outcome]:
    claimant = case.dispute.claimant
    if ruling.status is RulingStatus.PROPOSAL:
        return pending_outcomes()
    return [
        Outcome(party=party, ruling_summary=_route_decision(ruling, claimant, party) if case.dispute.category is DisputeCategory.ROUTE_DEVIATION else _decision(ruling, claimant, party), action_status=ActionStatus.RECOMMENDED)
        for party in Party
    ]


def pending_outcomes() -> list[Outcome]:
    """What both parties are told while a person reviews the Case, including when there is no Ruling at all."""
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


def _decision(ruling: Ruling, claimant: Party, reader: Party, category: DisputeCategory) -> str:
    whose = "Your claim" if reader is claimant else f"The {claimant.value}'s claim"
    reason = f" Reason: {ruling.reasoning_summary}"
    if category is DisputeCategory.SAFETY_INCIDENT:
        return _safety_decision(ruling, whose, reason)
    if ruling.outcome is RulingOutcome.REJECT:
        return f"{whose} was not upheld. The no-show fee stands.{reason}"
    amount = f"The {ruling.currency} {ruling.amount} no-show fee" if ruling.amount is not None else "The no-show fee"
    reversed_ = "will be reversed" if reader is claimant else "is reversed"
    return f"{whose} was upheld. {amount} {reversed_}.{reason}"


def _route_decision(ruling: Ruling, claimant: Party, reader: Party) -> str:
    whose = "Your claim" if reader is claimant else f"The {claimant.value}'s claim"
    if ruling.outcome is RulingOutcome.REJECT:
        decision = f"{whose} was rejected. No refund is recommended."
    else:
        label = "partially upheld" if ruling.outcome is RulingOutcome.PARTIALLY_UPHOLD else "upheld"
        decision = f"{whose} was {label}. A {ruling.currency} {ruling.amount} route-fare refund is recommended, not executed."
    return f"{decision} Reason: {ruling.reasoning_summary}"
