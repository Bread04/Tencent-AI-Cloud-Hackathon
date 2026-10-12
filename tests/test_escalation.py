"""Seams: apply_escalation(ruling, ...), run_dispute(..., switches=) and the review package/decision (ticket 09)."""

import pytest

from src.agents.escalation import apply_escalation
from src.config import CONFIG
from src.contracts import CaseStatus, LogEventKind, ReviewTrigger, RulingStatus, Switches
from src.intake import load_catalog
from src.orchestrator import run_dispute
from src.store import CaseStore

from tests.cases import a_stub_for
from tests.test_judge import a_judge_draft, run_judge

THRESHOLD = CONFIG.escalation.confidence_threshold


def a_final_ruling(confidence: float):
    """A real final Ruling from the Judge, with its Confidence set to the given value."""
    ruling, _ = run_judge(a_judge_draft())
    return ruling.model_copy(update={"confidence": ruling.confidence.model_copy(update={"value": confidence})})


# --- The decision: code, not a model -------------------------------------------------------------------------------


def test_a_ruling_below_the_threshold_is_not_finalized_and_says_why():
    ruling = apply_escalation(a_final_ruling(0.6), enabled=True, threshold=THRESHOLD)

    assert ruling.status is RulingStatus.PROPOSAL
    assert [t.trigger for t in ruling.review_triggers] == [ReviewTrigger.LOW_CONFIDENCE]
    assert "0.6" in ruling.review_triggers[0].reason and str(THRESHOLD) in ruling.review_triggers[0].reason


def test_a_ruling_at_the_threshold_is_finalized():
    ruling = apply_escalation(a_final_ruling(THRESHOLD), enabled=True, threshold=THRESHOLD)

    assert ruling.status is RulingStatus.FINAL and not ruling.review_triggers


def test_low_confidence_is_not_added_twice():
    once = apply_escalation(a_final_ruling(0.5), enabled=True, threshold=THRESHOLD)

    twice = apply_escalation(once, enabled=True, threshold=THRESHOLD)

    assert [t.trigger for t in twice.review_triggers].count(ReviewTrigger.LOW_CONFIDENCE) == 1


def test_a_threshold_set_higher_escalates_more():
    assert apply_escalation(a_final_ruling(0.8), enabled=True, threshold=0.9).status is RulingStatus.PROPOSAL


def test_with_escalation_off_a_proposal_is_finalized_as_before():
    proposal = apply_escalation(a_final_ruling(0.4), enabled=True, threshold=THRESHOLD)

    ruling = apply_escalation(proposal, enabled=False, threshold=THRESHOLD)

    assert ruling.status is RulingStatus.FINAL


# --- End to end ----------------------------------------------------------------------------------------------------


def run(dispute_id, switches=None):
    catalog, store = load_catalog(), CaseStore()
    case = run_dispute(catalog.dispute(dispute_id), store=store, model=a_stub_for("CASE-0001", dispute_id), catalog=catalog, switches=switches)
    return store, case


def test_a_mock_case_escalates_on_low_confidence_and_joins_the_queue():
    _, case = run("DISP-004")

    assert case.status is CaseStatus.PENDING_REVIEW
    assert ReviewTrigger.LOW_CONFIDENCE in [t.trigger for t in case.ruling.review_triggers]
    assert case.ruling.confidence.value < THRESHOLD
    assert {o.action_status.value for o in case.outcomes} == {"pending_review"}  # both parties are told review is pending


def test_the_headline_demo_case_resolves_after_the_history_step():
    _, case = run("DISP-002")

    assert case.status is CaseStatus.NOTIFIED
    assert case.ruling.confidence.value >= THRESHOLD
    assert len(case.ruling.history_adjustments) == 2  # both History rules still show as adjustments


def test_with_escalation_switched_off_every_ruling_finalizes():
    _, case = run("DISP-004", switches=Switches(escalation=False))

    assert case.status is CaseStatus.NOTIFIED
    assert case.ruling.status is RulingStatus.FINAL
    assert {o.action_status.value for o in case.outcomes} == {"recommended"}


def test_escalation_is_on_by_default_for_the_demo():
    assert CONFIG.switches.escalation is True
