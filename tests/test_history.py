"""Seam: apply_history(ruling, case, rules=) -> Ruling. History runs only after the outcome is fixed (ADR 0001)."""

import copy

import pytest

from src.agents.judge.history import apply_history
from src.config import HistoryRule
from src.contracts import ReviewTrigger, RulingStatus

from tests.builders import a_ruling
from tests.cases import a_sealed_no_show_case


def a_case_with_rider_history(**rider_changes):
    """The sealed DISP-002 case, with the rider's History changed. The rider is the Claimant."""
    _, case = a_sealed_no_show_case()
    evidence = copy.deepcopy(case.evidence)
    history = next(item for item in evidence if item.source == "history")
    history.content["rider"] |= rider_changes
    return case.model_copy(update={"evidence": evidence})


CLEAN = dict(dispute_history={"total_disputes": 1, "upheld": 1, "rejected": 0}, fraud_flags=0, fraud_flag_details=None)
THREE_REJECTED = dict(dispute_history={"total_disputes": 4, "upheld": 1, "rejected": 3}, fraud_flags=0, fraud_flag_details=None)
LATE_CANCELLER = dict(**CLEAN) | dict(fraud_flags=1, fraud_flag_details="flagged_for_frequent_late_cancellations")
FIVE_REJECTED = dict(dispute_history={"total_disputes": 6, "upheld": 1, "rejected": 5}, fraud_flags=0, fraud_flag_details=None)


def a_ruling_at(confidence, **overrides):
    return a_ruling(confidence={"value": confidence, "components": {"policy_fit": confidence}}, **overrides)


def test_a_clean_record_changes_nothing():
    ruling = a_ruling_at(0.8)

    assert apply_history(ruling, a_case_with_rider_history(**CLEAN)) == ruling


def test_each_rule_that_fires_lowers_confidence_by_one_step_and_is_listed_with_its_reason():
    ruling = apply_history(a_ruling_at(0.8), a_case_with_rider_history(**THREE_REJECTED))

    assert ruling.confidence.value == pytest.approx(0.75)
    assert [a.rule for a in ruling.history_adjustments] == ["prior_rejected"]
    assert ruling.history_adjustments[0].confidence_step == pytest.approx(0.05)
    assert "3" in ruling.history_adjustments[0].reason  # says what it saw


def test_the_total_cut_is_capped_at_the_configured_maximum():
    both = dict(THREE_REJECTED) | dict(fraud_flags=1, fraud_flag_details="flagged_for_frequent_late_cancellations")

    ruling = apply_history(a_ruling_at(0.8), a_case_with_rider_history(**both))

    assert [a.rule for a in ruling.history_adjustments] == ["prior_rejected", "late_cancel_flag"]
    assert ruling.confidence.value == pytest.approx(0.7)  # 0.8 less two steps of 0.05


def test_the_total_cut_is_capped_at_the_configured_maximum_however_many_rules_fire():
    from src.config import CONFIG

    rule = CONFIG.history_rules[0]

    ruling = apply_history(a_ruling_at(0.9), a_case_with_rider_history(**THREE_REJECTED), rules=(rule,) * 6)

    assert ruling.confidence.value == pytest.approx(0.9 - CONFIG.confidence.history_max)


def test_the_late_cancellation_flag_is_a_rule_of_its_own():
    ruling = apply_history(a_ruling_at(0.9), a_case_with_rider_history(**LATE_CANCELLER))

    assert [a.rule for a in ruling.history_adjustments] == ["late_cancel_flag"]


def test_three_prior_rejections_lower_confidence_but_do_not_trigger_review():
    ruling = apply_history(a_ruling_at(0.8), a_case_with_rider_history(**THREE_REJECTED))

    assert ruling.review_triggers == []
    assert ruling.status is not RulingStatus.PROPOSAL


def test_a_strong_prior_rejected_pattern_also_sends_the_case_to_review():
    ruling = apply_history(a_ruling_at(0.8), a_case_with_rider_history(**FIVE_REJECTED))

    assert ruling.confidence.value == pytest.approx(0.75)  # still lowers by one step
    assert [t.trigger for t in ruling.review_triggers] == [ReviewTrigger.HISTORY_RULE]
    assert ruling.status is RulingStatus.PROPOSAL


def test_history_can_never_raise_confidence_or_change_the_outcome_whoever_wins():
    case = a_case_with_rider_history(**THREE_REJECTED)
    for outcome, remedy in (("uphold", "fee_reversal"), ("reject", "no_action")):
        before = a_ruling_at(0.8, outcome=outcome, remedy=remedy, amount=None, currency=None, calculation=None)

        after = apply_history(before, case)

        assert after.confidence.value <= before.confidence.value
        assert (after.outcome, after.remedy, after.amount, after.balance_of_evidence) == (
            before.outcome,
            before.remedy,
            before.amount,
            before.balance_of_evidence,
        )


def test_confidence_never_goes_below_zero():
    assert apply_history(a_ruling_at(0.05), a_case_with_rider_history(**THREE_REJECTED)).confidence.value == 0


def test_the_input_ruling_is_left_untouched():
    ruling = a_ruling_at(0.8)

    apply_history(ruling, a_case_with_rider_history(**THREE_REJECTED))

    assert ruling.confidence.value == 0.8 and ruling.history_adjustments == []


def test_a_rule_that_calls_for_review_adds_a_trigger_and_makes_the_ruling_a_proposal():
    rules = (HistoryRule(key="late_cancel_flag", description="Flagged for late cancellations", lowers_confidence=False, triggers_review=True),)

    ruling = apply_history(a_ruling_at(0.8), a_case_with_rider_history(**LATE_CANCELLER), rules=rules)

    assert ruling.status is RulingStatus.PROPOSAL
    assert [t.trigger for t in ruling.review_triggers] == [ReviewTrigger.HISTORY_RULE]
    assert ruling.confidence.value == 0.8  # this rule only calls for review
    assert ruling.history_adjustments[0].confidence_step == 0


def test_a_case_without_history_evidence_is_left_alone():
    _, case = a_sealed_no_show_case()
    without = case.model_copy(update={"evidence": [item for item in case.evidence if item.source != "history"]})
    ruling = a_ruling_at(0.8)

    assert apply_history(ruling, without) == ruling
