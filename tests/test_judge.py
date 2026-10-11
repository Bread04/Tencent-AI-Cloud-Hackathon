"""Seam: judge(case, rider_submission, driver_submission, model) -> Ruling."""

import json
from decimal import Decimal

from src.agents.judge import judge
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
