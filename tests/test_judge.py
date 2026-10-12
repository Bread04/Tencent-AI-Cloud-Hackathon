"""Seam: judge(case, rider_submission, driver_submission, model) -> Ruling."""

import json

import pytest
from decimal import Decimal

from src.agents.judge import DraftRejected, judge
from src.config import CONFIG
from src.contracts import RulingOutcome, RulingStatus
from src.llm.stub import StubModel

from tests.cases import a_sealed_no_show_case, fixture_submissions


def a_judge_draft(**overrides):
    """What the model is scripted to return: the judgement only, no amount and no Confidence."""
    draft = dict(
        outcome="reject",
        balance_of_evidence="respondent",
        remedy="no_action",
        argument_assessments=[
            {
                "author": "rider_advocate",
                "argument": "The driver was not at the pickup point.",
                "verdict": "rejected",
                "reason": "GPS places the driver at the pickup point from arrival to cancellation.",
                "evidence_ids": ["EV-GPS-1"],
            },
            {
                "author": "driver_advocate",
                "argument": "The driver waited the full window and tried to make contact.",
                "verdict": "accepted",
                "reason": "GPS and chat show eight minutes at the pickup point and four messages plus a call.",
                "evidence_ids": ["EV-GPS-1", "EV-CHAT-1"],
            },
        ],
        policy_fit="clear",
        policy_fit_reason="The driver waited beyond the no-show threshold.",
        cited_evidence_ids=["EV-GPS-1", "EV-CHAT-1", "EV-FARE-1"],
        reasoning_summary="The driver was at the pickup point and the rider did not respond, so the fee stands.",
    )
    return draft | overrides


def run_judge(draft):
    store, case = a_sealed_no_show_case()
    rider, driver = fixture_submissions()
    model = StubModel({(case.case_id, "judge"): draft})
    return judge(case, rider, driver, model), model


def test_judge_returns_a_final_ruling_with_outcome_reasoning_and_calculated_confidence():
    ruling, _ = run_judge(a_judge_draft())

    assert ruling.status is RulingStatus.FINAL
    assert ruling.outcome is RulingOutcome.REJECT
    assert ruling.reasoning_summary
    assert ruling.amount is None  # nothing is paid out when the fee stands
    # Weakest link: the sample has no rider location, so 4 of the 5 material-evidence lines are available.
    assert ruling.confidence.value == 0.8
    assert ruling.confidence.components["evidence_completeness"] == 0.8
    assert ruling.confidence.components["policy_fit"] == 0.95


def test_judge_computes_the_amount_from_the_fare_evidence_not_from_the_model():
    ruling, _ = run_judge(
        a_judge_draft(outcome="uphold", balance_of_evidence="claimant", remedy="fee_reversal")
    )

    assert ruling.amount == Decimal("5.00")
    assert ruling.currency == "SGD"
    assert ruling.calculation.input_evidence_ids == ["EV-FARE-1"]


def test_judge_sees_both_submissions_but_never_the_history_of_either_party():
    _, model = run_judge(a_judge_draft())

    prompt = json.dumps(model.calls[0]["messages"])
    assert "RIDER-MARKER" in prompt and "DRIVER-MARKER" in prompt
    assert "EV-HISTORY-1" not in prompt
    assert "flagged_for_frequent_late_cancellations" not in prompt  # ADR 0001


@pytest.mark.parametrize(
    "outcome, remedy, complaint",
    [
        ("partially_uphold", "fee_reversal", "partial"),  # No-Show is all or nothing
        ("partially_uphold", "partial_refund", "partial"),
        ("uphold", "no_action", "fee_reversal"),  # an upheld claim must reverse the fee
        ("reject", "fee_reversal", "no_action"),  # a rejected claim must leave the fee
        ("uphold", "full_refund", "fee_reversal"),  # not a Remedy that applies to a No-Show fee
        ("uphold", "compensation_to_driver", "fee_reversal"),
    ],
)
def test_judge_refuses_a_draft_whose_outcome_and_remedy_are_not_allowed_for_a_no_show(outcome, remedy, complaint):
    claimant_leaning = "claimant" if outcome != "reject" else "respondent"
    draft = a_judge_draft(outcome=outcome, remedy=remedy, balance_of_evidence=claimant_leaning)

    with pytest.raises(DraftRejected, match=complaint):
        run_judge(draft)


def test_balanced_evidence_is_a_proposal_even_above_the_confidence_threshold():
    ruling, _ = run_judge(a_judge_draft(balance_of_evidence="balanced", policy_fit="arguable"))

    assert ruling.status is RulingStatus.PROPOSAL
    assert ruling.confidence.value == 0.75
    assert [record.trigger for record in ruling.review_triggers] == ["balanced_evidence"]


@pytest.mark.parametrize("balance, expected", [
    ("respondent", ["low_confidence"]),
    ("balanced", ["balanced_evidence", "low_confidence"]),
])
def test_low_computed_confidence_makes_the_draft_a_proposal(balance, expected):
    ruling, _ = run_judge(a_judge_draft(balance_of_evidence=balance, policy_fit="unclear"))

    assert ruling.status is RulingStatus.PROPOSAL
    assert ruling.confidence.value == 0.5
    assert [record.trigger for record in ruling.review_triggers] == expected
    assert str(CONFIG.escalation.confidence_threshold) in ruling.review_triggers[-1].reason


def test_low_confidence_trigger_uses_the_configured_threshold_and_is_strict(monkeypatch):
    # The unchanged DISP-002 completeness calculation is 0.8.
    monkeypatch.setattr("src.agents.judge.CONFIG", CONFIG.model_copy(update={
        "escalation": CONFIG.escalation.model_copy(update={"confidence_threshold": 0.8})
    }))
    ruling, _ = run_judge(a_judge_draft())
    assert ruling.status is RulingStatus.FINAL
    assert not ruling.review_triggers

    monkeypatch.setattr("src.agents.judge.CONFIG", CONFIG.model_copy(update={
        "escalation": CONFIG.escalation.model_copy(update={"confidence_threshold": 0.81})
    }))
    ruling, _ = run_judge(a_judge_draft())
    assert ruling.status is RulingStatus.PROPOSAL
    assert [record.trigger for record in ruling.review_triggers] == ["low_confidence"]


@pytest.mark.parametrize("balance, policy_fit, trigger", [
    ("claimant", "unclear", "low_confidence"),
    ("balanced", "arguable", "balanced_evidence"),
])
def test_fee_reversal_proposals_store_the_fare_derived_amount_and_matching_calculation(balance, policy_fit, trigger):
    store, case = a_sealed_no_show_case()
    rider, driver = fixture_submissions()
    model = StubModel({(case.case_id, "judge"): a_judge_draft(
        outcome="uphold", remedy="fee_reversal", balance_of_evidence=balance, policy_fit=policy_fit,
    )})
    ruling = judge(case, rider, driver, model)
    store.add_submission(case.case_id, rider)
    store.add_submission(case.case_id, driver)
    store.set_ruling(case.case_id, ruling)

    stored = store.get_case(case.case_id)
    fare = next(item for item in stored.evidence if item.source == "fare")
    assert stored.status == "pending_review"
    assert stored.ruling.status is RulingStatus.PROPOSAL
    assert stored.ruling.outcome == "uphold" and stored.ruling.remedy == "fee_reversal"
    assert [record.trigger for record in stored.ruling.review_triggers] == [trigger]
    assert stored.ruling.amount == Decimal(fare.derived["cancellation_fee"])
    assert stored.ruling.calculation.result == stored.ruling.amount
    assert stored.ruling.calculation.input_evidence_ids == [fare.evidence_id]
    assert not stored.outcomes
