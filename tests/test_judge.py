"""Seam: judge(case, rider_submission, driver_submission, model) -> Ruling."""

import json
from decimal import Decimal

import pytest

from src.agents.judge import DraftRejected, judge
from src.contracts import ArgumentVerdict, LogEventKind, ReviewTrigger, RulingOutcome, RulingStatus
from src.llm.repair import StageFailed
from src.llm.stub import StubModel

from tests.cases import a_sealed_no_show_case, fixture_submissions


UPHOLD = dict(outcome="uphold", remedy="fee_reversal")


def an_assessment(ref, verdict="accepted", reason="The sealed evidence supports it.", evidence_ids=("EV-GPS-1",)):
    return {"ref": ref, "verdict": verdict, "reason": reason, "evidence_ids": list(evidence_ids)}


def a_judge_draft(**overrides):
    """What the model is scripted to return: the judgement only, no amount and no Confidence."""
    draft = dict(
        outcome="reject",
        balance_of_evidence="respondent",
        remedy="no_action",
        argument_assessments=[
            an_assessment("rider_advocate#claim", "rejected", "GPS places the driver at the pickup point."),
            an_assessment("rider_advocate#counter-1", "not_decisive", "True, but it does not change the outcome."),
            an_assessment("driver_advocate#claim", "accepted", "GPS and chat show the driver waited and tried to call."),
            an_assessment("driver_advocate#counter-1", "accepted", "The driver waited the full free-wait period."),
        ],
        policy_fit="clear",
        policy_fit_reason="The driver waited beyond the no-show threshold.",
        cited_evidence_ids=["EV-GPS-1", "EV-CHAT-1", "EV-FARE-1"],
        reasoning_summary="The driver was at the pickup point and the rider did not respond, so the fee stands.",
    )
    return draft | overrides


SELF_CHECK_PASSES = {"supported": True, "problems": []}


def run_judge(draft, self_check=SELF_CHECK_PASSES, record=None):
    """Run the Judge on the sealed DISP-002 case. `draft` and `self_check` may be one reply or a list, one per call."""
    store, case = a_sealed_no_show_case()
    rider, driver = fixture_submissions()
    model = StubModel({(case.case_id, "judge"): draft, (case.case_id, "judge_self_check"): self_check})
    return judge(case, rider, driver, model, record=record), model


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
    ruling, _ = run_judge(a_judge_draft(**UPHOLD, balance_of_evidence="claimant", amount_input_evidence_ids=["EV-FARE-1"]))

    assert ruling.amount == Decimal("5.00")
    assert ruling.currency == "SGD"
    assert ruling.calculation.input_evidence_ids == ["EV-FARE-1"]
    assert ruling.calculation.result == ruling.amount  # the Ruling shows how the amount was reached
    assert ruling.calculation.formula


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


# --- Argument Assessments: every argument in both Submissions gets exactly one -------------------------


def test_every_claim_and_counter_argument_in_both_submissions_is_assessed_with_a_reason_and_evidence():
    rider, driver = fixture_submissions()

    ruling, _ = run_judge(a_judge_draft())

    assessed = [(a.author.value, a.argument) for a in ruling.argument_assessments]
    assert assessed == [
        ("rider_advocate", rider.claim_restated),
        ("rider_advocate", rider.counter_arguments[0].argument),
        ("driver_advocate", driver.claim_restated),
        ("driver_advocate", driver.counter_arguments[0].argument),
    ]
    assert {a.verdict for a in ruling.argument_assessments} <= set(ArgumentVerdict)
    assert all(a.reason and a.evidence_ids for a in ruling.argument_assessments)


def test_the_judge_is_told_the_reference_of_each_argument_it_must_assess():
    _, model = run_judge(a_judge_draft())

    prompt = json.dumps(model.calls[0]["messages"])
    for ref in ("rider_advocate#claim", "rider_advocate#counter-1", "driver_advocate#claim", "driver_advocate#counter-1"):
        assert ref in prompt


def test_a_draft_that_skips_an_argument_is_refused_and_names_it():
    skipped = a_judge_draft()["argument_assessments"][:-1]  # drops driver_advocate#counter-1

    with pytest.raises(DraftRejected, match="driver_advocate#counter-1"):
        run_judge(a_judge_draft(argument_assessments=skipped))


def test_a_draft_that_assesses_an_argument_twice_is_refused():
    doubled = a_judge_draft()["argument_assessments"] + [an_assessment("rider_advocate#claim", "rejected")]

    with pytest.raises(DraftRejected, match="more than once"):
        run_judge(a_judge_draft(argument_assessments=doubled))


def test_a_draft_that_assesses_an_argument_nobody_made_is_refused():
    extra = a_judge_draft()["argument_assessments"] + [an_assessment("rider_advocate#counter-9")]

    with pytest.raises(DraftRejected, match="counter-9"):
        run_judge(a_judge_draft(argument_assessments=extra))


# --- Burden of Proof, coherence and balanced evidence ---------------------------------------------------



@pytest.mark.parametrize("balance", ["respondent", "balanced"])
def test_a_claim_cannot_be_upheld_unless_the_evidence_leans_to_the_claimant(balance):
    with pytest.raises(DraftRejected, match="Burden of Proof"):
        run_judge(a_judge_draft(**UPHOLD, balance_of_evidence=balance))


def test_a_claim_cannot_be_rejected_while_the_draft_says_the_evidence_leans_to_the_claimant():
    with pytest.raises(DraftRejected, match="leans towards the claimant"):
        run_judge(a_judge_draft(balance_of_evidence="claimant"))


def test_an_unproven_claim_by_the_claimant_cannot_be_upheld():
    assessments = a_judge_draft()["argument_assessments"]
    assessments[0] = an_assessment("rider_advocate#claim", "unproven", "No record shows it.", ["EV-RIDERLOC-1"])

    with pytest.raises(DraftRejected, match="unproven"):
        run_judge(a_judge_draft(**UPHOLD, balance_of_evidence="claimant", argument_assessments=assessments))


def test_an_unproven_claim_by_the_claimant_is_rejected():
    assessments = a_judge_draft()["argument_assessments"]
    assessments[0] = an_assessment("rider_advocate#claim", "unproven", "No record shows it.", ["EV-RIDERLOC-1"])

    ruling, _ = run_judge(a_judge_draft(argument_assessments=assessments))

    assert ruling.outcome is RulingOutcome.REJECT
    assert ruling.argument_assessments[0].verdict is ArgumentVerdict.UNPROVEN


def test_evenly_balanced_evidence_gives_a_proposal_marked_for_review_not_a_final_ruling():
    ruling, _ = run_judge(a_judge_draft(balance_of_evidence="balanced"))

    assert ruling.status is RulingStatus.PROPOSAL
    assert ruling.balance_of_evidence.value == "balanced"
    assert [record.trigger for record in ruling.review_triggers] == [ReviewTrigger.BALANCED_EVIDENCE]
    assert ruling.review_triggers[0].reason


def test_a_clear_ruling_is_final_and_carries_no_review_trigger():
    ruling, _ = run_judge(a_judge_draft())

    assert ruling.status is RulingStatus.FINAL
    assert ruling.review_triggers == []


# --- The amount is computed from the inputs the Judge names ---------------------------------------------


def test_a_fee_reversal_that_names_no_input_for_its_amount_is_refused():
    with pytest.raises(DraftRejected, match="names no Evidence Item"):
        run_judge(a_judge_draft(**UPHOLD, balance_of_evidence="claimant"))


@pytest.mark.parametrize("named", [["EV-GPS-1"], ["EV-FARE-9"], ["EV-FARE-1", "EV-GPS-1"]])
def test_a_fee_reversal_whose_named_input_is_not_a_fare_item_is_refused(named):
    with pytest.raises(DraftRejected, match="not a fare Evidence Item"):
        run_judge(a_judge_draft(**UPHOLD, balance_of_evidence="claimant", amount_input_evidence_ids=named))


def test_a_ruling_with_no_amount_does_not_need_amount_inputs():
    ruling, _ = run_judge(a_judge_draft())

    assert ruling.amount is None and ruling.calculation is None


# --- Own Findings and Policy Gaps ------------------------------------------------------------------------


def an_own_finding(decisive, evidence_ids=("EV-FARE-1",)):
    return {
        "finding": "The fee was charged at 08:51, after the 8-minute no-show threshold, which neither advocate raised.",
        "evidence_ids": list(evidence_ids),
        "decisive": decisive,
    }


def test_a_point_neither_advocate_raised_is_labelled_as_an_own_finding():
    ruling, _ = run_judge(a_judge_draft(own_findings=[an_own_finding(decisive=False)]))

    assert [f.finding for f in ruling.own_findings] == [an_own_finding(False)["finding"]]
    assert ruling.own_findings[0].evidence_ids == ["EV-FARE-1"]


def test_a_decisive_own_finding_caps_confidence_at_the_configured_ceiling():
    ruling, _ = run_judge(a_judge_draft(own_findings=[an_own_finding(decisive=True)]))

    assert ruling.confidence.components["own_finding_cap"] == 0.75
    assert ruling.confidence.value == 0.75  # 0.8 from evidence completeness, capped


def test_a_finding_that_is_not_decisive_does_not_cap_confidence():
    ruling, _ = run_judge(a_judge_draft(own_findings=[an_own_finding(decisive=False)]))

    assert "own_finding_cap" not in ruling.confidence.components
    assert ruling.confidence.value == 0.8


def test_an_own_finding_must_rest_on_evidence_that_exists():
    with pytest.raises(StageFailed, match="EV-NOPE-1"):  # sent back for repair, then the stage fails
        run_judge(a_judge_draft(own_findings=[an_own_finding(True, evidence_ids=["EV-NOPE-1"])]))


def test_a_policy_gap_is_named_makes_policy_fit_unclear_and_marks_the_ruling_for_review():
    gap = "No clause says whether a rider who boards late but within the threshold owes the fee."

    ruling, _ = run_judge(a_judge_draft(policy_fit="unclear", policy_gap=gap))

    assert ruling.policy_gap == gap
    assert ruling.policy_fit.value == "unclear"
    assert ruling.confidence.components["policy_fit"] == 0.5
    assert ruling.status is RulingStatus.PROPOSAL
    assert [t.trigger for t in ruling.review_triggers] == [ReviewTrigger.POLICY_GAP]


def test_a_policy_gap_with_a_clear_policy_fit_is_refused():
    with pytest.raises(DraftRejected, match="unclear"):
        run_judge(a_judge_draft(policy_fit="clear", policy_gap="No clause covers it."))


def test_an_unclear_policy_fit_without_a_named_gap_is_refused():
    with pytest.raises(DraftRejected, match="name the gap"):
        run_judge(a_judge_draft(policy_fit="unclear"))


# --- The self-check and the send-back --------------------------------------------------------------------


def calls_to(model, agent):
    return [call for call in model.calls if call["agent"] == agent]


def test_the_judge_asks_a_second_call_whether_each_cited_item_supports_the_claim_made_about_it():
    events = []

    ruling, model = run_judge(a_judge_draft(), record=lambda kind, summary: events.append(kind))

    assert ruling.status is RulingStatus.FINAL
    assert len(calls_to(model, "judge_self_check")) == 1
    check_prompt = json.dumps(calls_to(model, "judge_self_check")[0]["messages"])
    assert "EV-GPS-1" in check_prompt  # it is shown the cited evidence and the claims made about it
    assert "EV-HISTORY-1" not in check_prompt  # ADR 0001 applies to every model call
    assert events == [LogEventKind.SELF_CHECK_PASSED]


def test_a_failed_self_check_sends_the_draft_back_once_with_the_problem_and_then_accepts_the_corrected_draft():
    failed = {"supported": False, "problems": ["EV-CHAT-1 does not show a call that went unanswered."]}
    events = []

    ruling, model = run_judge(
        [a_judge_draft(reasoning_summary="First draft."), a_judge_draft(reasoning_summary="Second draft.")],
        self_check=[failed, SELF_CHECK_PASSES],
        record=lambda kind, summary: events.append(kind),
    )

    assert ruling.reasoning_summary == "Second draft."
    judge_calls = calls_to(model, "judge")
    assert len(judge_calls) == 2
    assert "EV-CHAT-1 does not show a call" in json.dumps(judge_calls[1]["messages"])
    assert events == [LogEventKind.SELF_CHECK_FAILED, LogEventKind.SELF_CHECK_PASSED]


def test_a_draft_that_fails_the_self_check_twice_fails_the_stage_with_the_reason():
    failed = {"supported": False, "problems": ["EV-GPS-1 does not support the claim made about it."]}
    events = []

    with pytest.raises(StageFailed, match="EV-GPS-1 does not support"):
        run_judge(a_judge_draft(), self_check=failed, record=lambda kind, summary: events.append(kind))

    assert events == [LogEventKind.SELF_CHECK_FAILED, LogEventKind.SELF_CHECK_FAILED]


def test_a_draft_that_breaks_a_code_rule_is_sent_back_with_the_problem_and_the_corrected_draft_is_used():
    skipped = a_judge_draft()["argument_assessments"][:-1]

    ruling, model = run_judge([a_judge_draft(argument_assessments=skipped), a_judge_draft()])

    judge_calls = calls_to(model, "judge")
    assert len(judge_calls) == 2
    assert "driver_advocate#counter-1 has no assessment" in json.dumps(judge_calls[1]["messages"])
    assert len(ruling.argument_assessments) == 4


def test_a_reply_that_does_not_match_the_required_format_is_sent_back_and_repaired():
    malformed = {"outcome": "reject"}  # nothing else the schema requires

    ruling, model = run_judge([malformed, a_judge_draft()])

    assert len(calls_to(model, "judge")) == 2
    assert ruling.outcome is RulingOutcome.REJECT


def test_a_draft_still_breaking_a_rule_after_the_repair_budget_fails_the_stage():
    skipped = a_judge_draft()["argument_assessments"][:-1]

    with pytest.raises(StageFailed, match="driver_advocate#counter-1"):
        run_judge(a_judge_draft(argument_assessments=skipped))  # the same bad reply every time
