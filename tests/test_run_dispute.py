"""Seam: run_dispute(dispute, store=, model=, catalog=) -> Case. The whole pipeline on the stub."""

import json
import socket

import pytest

from src.agents.policy import policy_for
from src.contracts import ActionStatus, CaseStatus, DisputeCategory, EvidenceStatus, LogEventKind, RulingOutcome, RulingStatus
from src.intake import DEFAULT_DATA_DIR, load_catalog
from src.llm.stub import StubModel
from src.orchestrator import run_dispute
from src.store import CaseStore

from tests.builders import a_dispute
from tests.cases import DISPUTE_ID, a_stub_for, stub_replies


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the end-to-end run tried to open a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)


def run_prepared_dispute():
    catalog = load_catalog()
    store, model = CaseStore(), a_stub_for("CASE-0001")
    case = run_dispute(catalog.dispute(DISPUTE_ID), store=store, model=model, catalog=catalog)
    return store, model, case


def all_prompts(model: StubModel) -> str:
    return json.dumps([call["messages"] for call in model.calls])


def test_running_the_prepared_dispute_produces_a_ruled_case_with_a_ruling_and_both_parties_told():
    _, _, case = run_prepared_dispute()

    assert case.status is CaseStatus.NOTIFIED  # ruled, then both parties told
    assert case.ruling.outcome is RulingOutcome.REJECT
    assert case.ruling.reasoning_summary
    assert 0 < case.ruling.confidence.value <= 1


def test_the_case_holds_gps_chat_fare_and_history_evidence_with_ids_and_statuses():
    _, _, case = run_prepared_dispute()

    by_source = {item.source: item for item in case.evidence}
    assert {"gps", "chat", "fare", "history"} <= set(by_source)
    assert all(item.evidence_id and item.status in EvidenceStatus for item in case.evidence)
    assert case.evidence_version  # sealed before anyone argued


def test_the_communication_log_tells_the_story_in_order():
    store, _, case = run_prepared_dispute()

    assert [event.kind for event in store.log(case.case_id)] == [
        LogEventKind.CASE_FILED,
        LogEventKind.EVIDENCE_REQUESTED,
        LogEventKind.EVIDENCE_RETURNED,
        LogEventKind.EVIDENCE_SEALED,
        LogEventKind.POLICY_RETRIEVED,
        LogEventKind.SUBMISSION_FILED,
        LogEventKind.SUBMISSION_FILED,
        LogEventKind.SELF_CHECK_PASSED,
        LogEventKind.RULING_DRAFTED,
        LogEventKind.OUTCOME_SENT,
        LogEventKind.OUTCOME_SENT,
    ]


def test_each_advocate_files_a_submission_and_neither_sees_the_other():
    _, model, case = run_prepared_dispute()
    replies = stub_replies()
    rider_claim = replies["rider_advocate"]["claim_restated"]
    driver_claim = replies["driver_advocate"]["claim_restated"]

    assert {s.author.value for s in case.submissions} == {"rider_advocate", "driver_advocate"}
    prompts = {call["agent"]: json.dumps(call["messages"]) for call in model.calls}
    assert driver_claim not in prompts["rider_advocate"]
    assert rider_claim not in prompts["driver_advocate"]
    assert rider_claim in prompts["judge"] and driver_claim in prompts["judge"]


def test_no_agent_is_given_the_expected_outcome_label_or_either_partys_history():
    _, model, _ = run_prepared_dispute()
    label = json.loads((DEFAULT_DATA_DIR / "disp-002.eval.json").read_text(encoding="utf-8"))

    prompts = all_prompts(model)
    assert label["expected_summary"] not in prompts
    assert "expected_outcome" not in prompts
    assert "flagged_for_frequent_late_cancellations" not in prompts  # ADR 0001: no History in any prompt


def test_a_dispute_on_an_unknown_trip_is_rejected_with_a_clear_reason_and_no_model_call():
    catalog, store, model = load_catalog(), CaseStore(), StubModel({})

    case = run_dispute(a_dispute(trip_id="TRIP-DOES-NOT-EXIST"), store=store, model=model, catalog=catalog)

    assert case.status is CaseStatus.REJECTED
    rejection = store.log(case.case_id)[-1]
    assert rejection.kind is LogEventKind.CASE_REJECTED
    assert "TRIP-DOES-NOT-EXIST" in rejection.summary
    assert model.calls == []


def test_a_dispute_in_a_category_this_build_cannot_resolve_is_rejected_with_a_clear_reason():
    catalog, store, model = load_catalog(), CaseStore(), StubModel({})
    dispute = a_dispute(trip_id="TRIP-2026-09945", category="property_damage")

    case = run_dispute(dispute, store=store, model=model, catalog=catalog)

    assert case.status is CaseStatus.REJECTED
    assert "property_damage" in store.log(case.case_id)[-1].summary
    assert model.calls == []


def test_the_policy_is_retrieved_logged_stored_and_given_to_both_advocates_and_the_judge():
    store, model, case = run_prepared_dispute()

    expected = policy_for(DisputeCategory.NO_SHOW_CHARGE)
    assert case.policy_clauses == expected
    event = next(e for e in store.log(case.case_id) if e.kind is LogEventKind.POLICY_RETRIEVED)
    assert event.references == [clause.clause_id for clause in expected]
    given_policy = [call for call in model.calls if call["agent"] in {"rider_advocate", "driver_advocate", "judge"}]
    assert len(given_policy) == 3
    for call in given_policy:
        prompt = json.dumps(call["messages"])
        assert all(clause.clause_id in prompt for clause in expected), call["agent"]


def run_with_scripted_changes(agent: str, **changes):
    catalog, store = load_catalog(), CaseStore()
    replies = stub_replies()
    replies[agent] = replies[agent] | changes
    model = StubModel({("CASE-0001", name): reply for name, reply in replies.items()})
    case = run_dispute(catalog.dispute(DISPUTE_ID), store=store, model=model, catalog=catalog)
    return store, case


def test_an_advocate_citing_a_policy_clause_that_does_not_exist_sends_the_case_to_review_with_the_reason():
    store, case = run_with_scripted_changes("driver_advocate", policy_clause_ids=["NS-1", "NS-99"])

    assert case.status is CaseStatus.PENDING_REVIEW
    assert case.ruling is None
    assert "NS-99" in next(e.summary for e in store.log(case.case_id) if e.kind is LogEventKind.ESCALATED)


def test_an_advocate_cannot_quote_a_missing_evidence_item_as_fact():
    store, case = run_with_scripted_changes("rider_advocate", facts_relied_on=["EV-FARE-1", "EV-RIDERLOC-1"])

    reason = next(e.summary for e in store.log(case.case_id) if e.kind is LogEventKind.ESCALATED)
    assert case.status is CaseStatus.PENDING_REVIEW
    assert "EV-RIDERLOC-1" in reason and "missing" in reason


# --- The finished run: History, Outcomes and the review state --------------------------------------------


def run_with_reply(agent: str, reply):
    """Run the prepared Dispute with one agent's scripted reply replaced outright (a list is one reply per call)."""
    catalog, store = load_catalog(), CaseStore()
    replies = stub_replies() | {agent: reply}
    model = StubModel({("CASE-0001", name): value for name, value in replies.items()})
    case = run_dispute(catalog.dispute(DISPUTE_ID), store=store, model=model, catalog=catalog)
    return store, model, case


def test_history_lowers_confidence_after_the_outcome_is_fixed_and_never_changes_the_outcome():
    _, _, case = run_prepared_dispute()

    # The rider has 3 prior rejected disputes and a late-cancellation flag, so both rules fire: 0.8 less 0.2.
    assert [a.rule for a in case.ruling.history_adjustments] == ["prior_rejected", "late_cancel_flag"]
    assert case.ruling.confidence.value == pytest.approx(0.6)
    assert case.ruling.outcome is RulingOutcome.REJECT  # History never decides


def test_both_parties_get_an_outcome_that_is_recommended_not_executed():
    _, _, case = run_prepared_dispute()

    assert {o.party.value for o in case.outcomes} == {"rider", "driver"}
    assert {o.action_status for o in case.outcomes} == {ActionStatus.RECOMMENDED}


def test_evenly_balanced_evidence_puts_the_case_in_review_with_a_proposal_and_a_pending_outcome():
    store, _, case = run_with_reply("judge", stub_replies()["judge"] | {"balance_of_evidence": "balanced"})

    assert case.status is CaseStatus.PENDING_REVIEW
    assert case.ruling.status is RulingStatus.PROPOSAL
    assert {o.action_status for o in case.outcomes} == {ActionStatus.PENDING_REVIEW}
    escalation = next(e for e in store.log(case.case_id) if e.kind is LogEventKind.ESCALATED)
    assert "balanced" in escalation.summary.lower()


def test_a_judge_that_fails_its_self_check_twice_sends_the_case_to_review_with_the_reason_and_no_ruling():
    failed = {"supported": False, "problems": ["EV-GPS-1 does not support the claim made about it."]}

    store, _, case = run_with_reply("judge_self_check", failed)

    assert case.status is CaseStatus.PENDING_REVIEW
    assert case.ruling is None  # never a made-up Ruling
    assert {o.action_status for o in case.outcomes} == {ActionStatus.PENDING_REVIEW}
    escalation = next(e for e in store.log(case.case_id) if e.kind is LogEventKind.ESCALATED)
    assert "EV-GPS-1 does not support" in escalation.summary


def test_a_judge_citing_a_policy_clause_that_does_not_exist_is_repaired_then_sent_to_review_with_the_reason():
    store, model, case = run_with_reply("judge", stub_replies()["judge"] | {"cited_policy_clause_ids": ["NS-99"]})

    assert case.status is CaseStatus.PENDING_REVIEW and case.ruling is None
    assert len([c for c in model.calls if c["agent"] == "judge"]) == 3  # the first reply and two repairs
    assert "NS-99" in next(e for e in store.log(case.case_id) if e.kind is LogEventKind.ESCALATED).summary


def test_a_judge_resting_a_ruling_on_a_missing_evidence_item_is_sent_to_review():
    store, _, case = run_with_reply("judge", stub_replies()["judge"] | {"cited_evidence_ids": ["EV-GPS-1", "EV-RIDERLOC-1"]})

    assert case.status is CaseStatus.PENDING_REVIEW and case.ruling is None
    assert "missing" in next(e for e in store.log(case.case_id) if e.kind is LogEventKind.ESCALATED).summary
