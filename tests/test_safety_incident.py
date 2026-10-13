"""Seam: run_dispute with SLA routing (ticket 13). A Safety Incident gets the highest Priority and always goes to a person."""

import time

import pytest
from fastapi.testclient import TestClient

from src.agents.escalation import decide_review
from src.agents.routing import CATEGORY_POINTS
from src.config import CONFIG
from src.api.demo import ReplayModel, create_demo_app
from src.contracts import CaseStatus, DisputeCategory, LogEventKind, ReviewDecision, ReviewTrigger, Switches
from src.intake import load_catalog
from src.orchestrator import run_dispute
from src.store import CaseStore

ROUTING = Switches(sla_routing=True, escalation=True)


def run(dispute_id, switches=ROUTING, store=None):
    catalog, store = load_catalog(), store or CaseStore()
    case = run_dispute(catalog.dispute(dispute_id), store=store, model=ReplayModel(store), catalog=catalog, switches=switches)
    return store, case


# --- Every Case gets a Priority and a reason -------------------------------------------------------------------------------------


def test_a_case_gets_a_priority_and_its_reason_when_filed_and_the_log_says_so():
    store, case = run("DISP-004")

    assert case.priority > 0 and "no show charge" in case.priority_reason
    event = next(e for e in store.log(case.case_id) if e.kind is LogEventKind.PRIORITY_SET)
    assert str(case.priority) in event.summary and case.priority_reason in event.summary


def test_with_the_switch_off_every_case_shares_one_priority_and_earlier_cases_still_resolve():
    store = CaseStore()
    _, quiet = run("DISP-002", Switches(escalation=True), store)
    _, held = run("DISP-004", Switches(escalation=True), store)

    assert quiet.priority == held.priority == 0 and quiet.priority_reason is None
    assert quiet.status is CaseStatus.NOTIFIED
    assert not [e for e in store.log(quiet.case_id) if e.kind is LogEventKind.PRIORITY_SET]


# --- Safety Incidents -----------------------------------------------------------------------------------------------------------


def test_a_safety_incident_gets_the_highest_priority():
    store = CaseStore()
    _, ordinary = run("DISP-004", store=store)
    _, safety = run("DISP-005", store=store)

    assert safety.priority > ordinary.priority
    assert "safety incident" in safety.priority_reason


@pytest.mark.parametrize("dispute_id, outcome", [("DISP-005", "uphold"), ("DISP-006", "reject")])
def test_a_safety_incident_is_always_held_for_a_person_even_when_the_judge_is_confident(dispute_id, outcome):
    _, case = run(dispute_id)

    assert case.ruling.outcome.value == outcome
    assert case.ruling.confidence.value >= CONFIG.escalation.confidence_threshold  # confident, and still held
    assert case.status is CaseStatus.PENDING_REVIEW
    assert [t.trigger for t in case.ruling.review_triggers] == [ReviewTrigger.SAFETY_INCIDENT]
    assert {o.action_status.value for o in case.outcomes} == {"pending_review"}


def test_a_safety_incident_is_held_even_with_the_escalation_switch_off():
    _, case = run("DISP-005", Switches(sla_routing=True, escalation=False))

    assert case.status is CaseStatus.PENDING_REVIEW


def test_without_the_routing_switch_a_safety_incident_is_still_taken_and_held_for_a_person_with_no_priority():
    store, case = run("DISP-005", Switches(escalation=True))

    assert case.status is CaseStatus.PENDING_REVIEW and case.priority == 0
    assert not [e for e in store.log(case.case_id) if e.kind is LogEventKind.CASE_REJECTED]
    sent = next(e for e in store.log(case.case_id) if e.kind is LogEventKind.ESCALATED)
    assert "Safety Officer" in sent.summary and "no Priority" in sent.summary  # ADR 0006: the reason it has no Priority is stated


def test_a_safety_incident_is_sent_to_a_safety_officer_at_filing_before_any_evidence_is_gathered():
    store, case = run("DISP-005")

    kinds = [e.kind for e in store.log(case.case_id)]
    assert kinds.index(LogEventKind.ESCALATED) < kinds.index(LogEventKind.EVIDENCE_REQUESTED)


def test_the_reporter_is_told_a_safety_officer_has_it_and_the_other_party_is_told_nothing_of_the_allegation():
    _, case = run("DISP-005")  # filed by the rider

    told = {o.party.value: o.ruling_summary for o in case.outcomes}
    assert "Safety Officer" in told["rider"] and "priority" in told["rider"]
    assert "Safety" not in told["driver"] and "safety" not in told["driver"].lower() and "report" in told["driver"]
    assert {o.action_status.value for o in case.outcomes} == {"pending_review"}


def test_the_reviewer_can_confirm_a_safety_incident_and_the_parties_are_told_in_words_that_fit():
    store, case = run("DISP-005")

    decided = decide_review(store, case.case_id, reviewer="Dana", decision=ReviewDecision.CONFIRM)

    told = " ".join(o.ruling_summary for o in decided.outcomes)
    assert decided.status is CaseStatus.NOTIFIED and "full refund" in told.lower()
    assert "no-show" not in told.lower()


# --- The review queue is ordered by Priority ---------------------------------------------------------------------------------------


@pytest.fixture
def client():
    return TestClient(create_demo_app())


def run_and_wait(client, dispute_id):
    case_id = client.post(f"/api/disputes/{dispute_id}/run?routing=true").json()["case_id"]
    for _ in range(100):
        if client.get(f"/api/cases/{case_id}").json()["case"]["outcomes"]:
            return case_id
        time.sleep(0.05)
    raise AssertionError("the run did not finish")


def test_a_safety_incident_filed_last_appears_first_in_the_queue_with_its_priority_and_reason(client):
    first = run_and_wait(client, "DISP-004")
    second = run_and_wait(client, "DISP-004")
    last = run_and_wait(client, "DISP-005")

    queue = client.get("/api/review").json()["cases"]

    assert [item["case_id"] for item in queue] == [last, first, second]  # priority first, then oldest first
    assert queue[0]["priority"] > queue[1]["priority"] and "safety incident" in queue[0]["priority_reason"]


def reviewer_client(store):
    from fastapi import FastAPI

    from src.api.review import add_review_routes

    app = FastAPI()
    add_review_routes(app, store=store, simulated="simulated", model_label="scripted replies")
    return TestClient(app)


def test_a_safety_incident_is_in_the_queue_from_filing_awaiting_its_proposal_and_ahead_of_every_other_case():
    catalog, store = load_catalog(), CaseStore()
    run("DISP-004", ROUTING, store)  # an ordinary held case, filed first
    filed = store.create_case(catalog.dispute("DISP-005"), Switches())  # a Safety Incident that has only just been filed: no Judge yet, no Priority

    queue = reviewer_client(store).get("/api/review").json()["cases"]

    assert queue[0]["case_id"] == filed.case_id and queue[0]["awaiting_proposal"] and queue[0]["safety_officer"]
    assert queue[0]["proposed_outcome"] is None and not queue[1]["awaiting_proposal"]


def test_the_review_screen_refuses_a_decision_until_the_proposal_is_there():
    catalog, store = load_catalog(), CaseStore()
    filed = store.create_case(catalog.dispute("DISP-005"), Switches())

    answer = reviewer_client(store).post(f"/api/review/{filed.case_id}/decision", json={"reviewer": "Dana", "decision": "confirm"})

    assert answer.status_code == 409


def test_the_case_json_carries_the_priority_for_the_console(client):
    case_id = run_and_wait(client, "DISP-005")

    case = client.get(f"/api/cases/{case_id}").json()["case"]

    assert case["priority"] >= CATEGORY_POINTS[DisputeCategory.SAFETY_INCIDENT] and case["priority_reason"]
