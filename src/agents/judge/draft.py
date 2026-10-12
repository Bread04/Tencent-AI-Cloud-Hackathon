"""The model's draft Ruling and the rules code checks it against before it becomes a Ruling.

`draft_problems` returns every problem as a sentence written to be fed back to
the model, so a send-back can name all of them at once.
"""

from src.agents.judge.arguments import Argument, assessment_problems
from src.agents.policy import ALLOWED_REMEDIES
from src.llm.repair import StageFailed
from src.contracts import (
    Advocate,
    ArgumentVerdict,
    BalanceOfEvidence,
    Case,
    Contract,
    OwnFinding,
    Party,
    PolicyFit,
    Remedy,
    RulingOutcome,
    Text,
)


class DraftRejected(StageFailed):
    """The model's draft still breaks a rule enforced in code after the repair budget: the stage fails."""


class DraftAssessment(Contract):
    """The model's verdict on one numbered argument. Code turns it into an Argument Assessment."""

    ref: Text
    verdict: ArgumentVerdict
    reason: Text
    evidence_ids: list[str] = []


class JudgeDraft(Contract):
    """What the model returns. Everything else in the Ruling is filled in by code."""

    outcome: RulingOutcome
    balance_of_evidence: BalanceOfEvidence
    remedy: Remedy
    argument_assessments: list[DraftAssessment]
    policy_fit: PolicyFit
    policy_fit_reason: Text
    cited_evidence_ids: list[str] = []
    cited_policy_clause_ids: list[str] = []
    cited_precedent_ids: list[str] = []  # precedents it relied on; each must have been shown
    precedent_departure: str | None = None  # why its Remedy differs from a precedent that was shown
    amount_input_evidence_ids: list[str] = []  # the Evidence Items the amount comes from; code does the arithmetic
    own_findings: list[OwnFinding] = []  # points neither advocate raised, from the sealed evidence only
    policy_gap: str | None = None  # a situation no clause covers; the closest clause is applied
    reasoning_summary: Text


def draft_problems(case: Case, arguments: list[Argument], draft: JudgeDraft) -> list[str]:
    return [
        *_remedy_problems(case, draft),
        *assessment_problems(arguments, [assessment.ref for assessment in draft.argument_assessments]),
        *_burden_problems(case, draft),
        *_amount_problems(case, draft),
        *_policy_gap_problems(draft),
        *_precedent_problems(case, draft),
    ]


def _remedy_problems(case: Case, draft: JudgeDraft) -> list[str]:
    category = case.dispute.category
    allowed = ALLOWED_REMEDIES[category]
    if draft.outcome not in allowed:
        return [
            f"A {draft.outcome.value} outcome on a {category.value} needs a Policy Clause that provides for it. "
            "None does: a partial outcome is not available, so the claim is upheld or rejected in full."
        ]
    if draft.remedy is not allowed[draft.outcome]:
        return [
            f"An {draft.outcome.value} outcome on a {category.value} must use the remedy "
            f"{allowed[draft.outcome].value}, not {draft.remedy.value}."
        ]
    return []


def claimant_advocate(case: Case) -> Advocate:
    return Advocate.RIDER_ADVOCATE if case.dispute.claimant is Party.RIDER else Advocate.DRIVER_ADVOCATE


def _burden_problems(case: Case, draft: JudgeDraft) -> list[str]:
    """The Claimant must show the claim is more likely than not; an unproven claim is rejected."""
    problems = []
    claim_ref = f"{claimant_advocate(case).value}#claim"
    claim_verdict = next((a.verdict for a in draft.argument_assessments if a.ref == claim_ref), None)
    if draft.outcome is RulingOutcome.UPHOLD:
        if draft.balance_of_evidence is not BalanceOfEvidence.CLAIMANT:
            problems.append(
                "The draft upholds the claim, but says the evidence does not lean towards the claimant. "
                "The claimant bears the Burden of Proof."
            )
        if claim_verdict is ArgumentVerdict.UNPROVEN:
            problems.append("The draft upholds the claim, but assesses the claimant's own claim as unproven. An unproven claim is rejected.")
    if draft.outcome is RulingOutcome.REJECT and draft.balance_of_evidence is BalanceOfEvidence.CLAIMANT:
        problems.append("The draft rejects the claim, but says the evidence leans towards the claimant.")
    return problems


def _amount_problems(case: Case, draft: JudgeDraft) -> list[str]:
    if draft.remedy is not Remedy.FEE_REVERSAL:
        return []
    if not draft.amount_input_evidence_ids:
        return ["The draft reverses the fee but names no Evidence Item the amount comes from. Name the fare item."]
    fare_ids = {item.evidence_id for item in case.evidence if item.source == "fare"}
    return [
        f"{evidence_id} is not a fare Evidence Item, so the amount cannot be computed from it."
        for evidence_id in draft.amount_input_evidence_ids
        if evidence_id not in fare_ids
    ]


def _policy_gap_problems(draft: JudgeDraft) -> list[str]:
    if draft.policy_gap and draft.policy_fit is not PolicyFit.UNCLEAR:
        return ["The draft names a Policy Gap, so Policy Fit must be unclear."]
    if draft.policy_fit is PolicyFit.UNCLEAR and not draft.policy_gap:
        return ["The draft says Policy Fit is unclear but does not name the gap; name the gap, the situation no clause covers."]
    return []


def _precedent_problems(case: Case, draft: JudgeDraft) -> list[str]:
    """Precedent is advisory, but a Remedy that differs from one the Judge was shown needs a stated reason."""
    differing = [p for p in case.precedents if p.ruling.remedy is not draft.remedy]
    if not differing or (draft.precedent_departure or "").strip():
        return []
    ids = ", ".join(f"{p.precedent_id} ({p.ruling.remedy.value})" for p in differing)
    return [
        f"The Remedy {draft.remedy.value} differs from the precedent(s) shown: {ids}. "
        "Say in precedent_departure why this Case is different, or follow the precedent."
    ]
