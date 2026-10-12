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


# --- The review package ----------------------------------------------------------------------------------------------

from src.agents.escalation import ReviewError, decide_review, review_package  # noqa: E402
from src.contracts import ActionStatus, ReviewDecision, RulingOutcome  # noqa: E402
from src.llm import ModelError  # noqa: E402


class DeadModel:
    def complete(self, messages, *, case_id, agent, schema=None, images=None):
        raise ModelError("The model timed out after 30 seconds (agent judge).")


def a_held_case(dispute_id="DISP-004"):
    store, case = run(dispute_id)
    return store, case


def test_the_review_package_holds_everything_a_reviewer_needs():
    store, case = a_held_case()

    package = review_package(case, store.log(case.case_id))

    assert package.case_id == case.case_id and package.dispute.dispute_id == "DISP-004"
    assert package.proposed_ruling.status is RulingStatus.PROPOSAL
    assert len(package.submissions) == 2
    assert {item.evidence_id for item in package.evidence} >= {"EV-GPS-1", "EV-CHAT-1", "EV-FARE-1"}
    assert {c.clause_id for c in package.policy_clauses} >= set(package.proposed_ruling.cited_policy_clause_ids)
    assert {r.trigger for r in package.reasons} >= {ReviewTrigger.LOW_CONFIDENCE, ReviewTrigger.BALANCED_EVIDENCE, ReviewTrigger.POLICY_GAP}


def test_a_case_held_because_the_model_failed_has_a_package_with_no_ruling_and_the_reason():
    catalog, store = load_catalog(), CaseStore()
    case = run_dispute(catalog.dispute("DISP-003"), store=store, model=DeadModel(), catalog=catalog)

    package = review_package(case, store.log(case.case_id))

    assert package.proposed_ruling is None
    assert package.reasons[0].trigger is ReviewTrigger.STAGE_FAILED
    assert "timed out" in package.reasons[0].reason


# --- The reviewer's decision ----------------------------------------------------------------------------------------


def test_confirming_finalizes_the_ruling_and_tells_both_parties_the_final_outcome():
    store, case = a_held_case()

    decided = decide_review(store, case.case_id, reviewer="Dana", decision=ReviewDecision.CONFIRM)

    assert decided.status is CaseStatus.NOTIFIED
    assert decided.ruling.status is RulingStatus.FINAL
    assert decided.ruling.outcome is case.ruling.outcome
    assert decided.review_record.reviewer == "Dana" and decided.review_record.decision is ReviewDecision.CONFIRM
    assert [o.action_status for o in decided.outcomes] == [ActionStatus.RECOMMENDED, ActionStatus.RECOMMENDED]
    assert LogEventKind.REVIEW_DECISION in [e.kind for e in store.log(case.case_id)]


def test_an_override_needs_a_reason():
    store, case = a_held_case()

    with pytest.raises(ReviewError, match="reason"):
        decide_review(store, case.case_id, reviewer="Dana", decision=ReviewDecision.OVERRIDE, reason="  ")

    assert store.get_case(case.case_id).status is CaseStatus.PENDING_REVIEW  # nothing changed


def test_an_override_reverses_the_outcome_with_the_amount_recomputed_and_records_why():
    store, case = a_held_case()
    assert case.ruling.outcome is RulingOutcome.REJECT

    decided = decide_review(store, case.case_id, reviewer="Dana", decision=ReviewDecision.OVERRIDE, reason="Telemetry gap favours the rider.")

    assert decided.ruling.outcome is RulingOutcome.UPHOLD and decided.ruling.remedy.value == "fee_reversal"
    assert str(decided.ruling.amount) == "5.00" and decided.ruling.calculation.result == decided.ruling.amount
    assert decided.review_record.reason == "Telemetry gap favours the rider."
    assert "Telemetry gap favours the rider." in decided.ruling.reasoning_summary
    assert decided.status is CaseStatus.NOTIFIED
    assert "reversed" in next(o for o in decided.outcomes if o.party.value == "rider").ruling_summary


def test_a_case_that_is_not_pending_review_cannot_be_decided():
    store, case = run("DISP-003")

    with pytest.raises(ReviewError, match="not pending review"):
        decide_review(store, case.case_id, reviewer="Dana", decision=ReviewDecision.CONFIRM)


def test_a_case_with_no_proposed_ruling_cannot_be_confirmed_or_overridden():
    catalog, store = load_catalog(), CaseStore()
    case = run_dispute(catalog.dispute("DISP-003"), store=store, model=DeadModel(), catalog=catalog)

    with pytest.raises(ReviewError, match="no proposed Ruling"):
        decide_review(store, case.case_id, reviewer="Dana", decision=ReviewDecision.CONFIRM)


def test_a_decision_needs_a_reviewer_name():
    store, case = a_held_case()

    with pytest.raises(ReviewError, match="reviewer"):
        decide_review(store, case.case_id, reviewer=" ", decision=ReviewDecision.CONFIRM)


def test_a_decision_cannot_be_made_twice():
    store, case = a_held_case()
    decide_review(store, case.case_id, reviewer="Dana", decision=ReviewDecision.CONFIRM)

    with pytest.raises(ReviewError, match="not pending review"):
        decide_review(store, case.case_id, reviewer="Sam", decision=ReviewDecision.OVERRIDE, reason="Changed my mind.")
