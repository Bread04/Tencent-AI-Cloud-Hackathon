"""Seam: the reviewer's JSON API and page. The demo app runs on the scripted stub (see conftest), so no test calls a live model."""

import time

import pytest
from fastapi.testclient import TestClient

from src.api.demo import create_demo_app


@pytest.fixture
def client():
    return TestClient(create_demo_app())


def run_and_wait(client, dispute_id):
    case_id = client.post(f"/api/disputes/{dispute_id}/run").json()["case_id"]
    for _ in range(100):
        if client.get(f"/api/cases/{case_id}").json()["case"]["outcomes"]:
            return case_id
        time.sleep(0.05)
    raise AssertionError("the run did not finish")


def test_the_queue_is_empty_until_a_case_is_held(client):
    assert client.get("/api/review").json() == {"cases": []}


def test_a_held_case_joins_the_queue_with_its_reasons_and_a_decided_case_does_not(client):
    held = run_and_wait(client, "DISP-004")
    run_and_wait(client, "DISP-003")

    queue = client.get("/api/review").json()["cases"]

    assert [item["case_id"] for item in queue] == [held]
    assert queue[0]["dispute_id"] == "DISP-004"
    assert {r["trigger"] for r in queue[0]["reasons"]} >= {"low_confidence", "balanced_evidence", "policy_gap"}
    assert queue[0]["confidence"] == 0.5


def test_the_review_package_has_both_submissions_the_evidence_the_policy_and_the_proposed_ruling(client):
    held = run_and_wait(client, "DISP-004")

    package = client.get(f"/api/review/{held}").json()

    assert len(package["submissions"]) == 2
    assert package["evidence"] and package["policy_clauses"]
    assert package["proposed_ruling"]["status"] == "proposal"
    assert package["reasons"]


def test_an_unknown_case_is_a_clear_404(client):
    assert client.get("/api/review/CASE-9999").status_code == 404


def test_confirming_through_the_api_finalizes_the_case_and_removes_it_from_the_queue(client):
    held = run_and_wait(client, "DISP-004")

    response = client.post(f"/api/review/{held}/decision", json={"reviewer": "Dana", "decision": "confirm"})

    assert response.status_code == 200
    assert response.json()["case"]["status"] == "notified"
    assert client.get("/api/review").json() == {"cases": []}


def test_an_override_without_a_reason_is_refused_and_changes_nothing(client):
    held = run_and_wait(client, "DISP-004")

    response = client.post(f"/api/review/{held}/decision", json={"reviewer": "Dana", "decision": "override", "reason": ""})

    assert response.status_code == 422
    assert "reason" in response.json()["error"]
    assert [item["case_id"] for item in client.get("/api/review").json()["cases"]] == [held]


def test_an_override_with_a_reason_reverses_the_ruling(client):
    held = run_and_wait(client, "DISP-004")

    response = client.post(f"/api/review/{held}/decision", json={"reviewer": "Dana", "decision": "override", "reason": "Gap favours the rider."})

    ruling = response.json()["case"]["ruling"]
    assert ruling["outcome"] == "uphold" and ruling["amount"] == "5.00"


def test_deciding_a_case_that_is_not_pending_is_a_conflict(client):
    decided = run_and_wait(client, "DISP-003")

    response = client.post(f"/api/review/{decided}/decision", json={"reviewer": "Dana", "decision": "confirm"})

    assert response.status_code == 409
    assert "not pending review" in response.json()["error"]


def test_a_decision_that_is_not_confirm_or_override_is_refused(client):
    held = run_and_wait(client, "DISP-004")

    assert client.post(f"/api/review/{held}/decision", json={"reviewer": "Dana", "decision": "shrug"}).status_code == 422


def test_the_reviewer_screen_is_a_page_and_the_console_links_to_it(client):
    screen = client.get("/review")

    assert screen.status_code == 200 and "Review queue" in screen.text and "review.js" in screen.text
    assert 'href="/review"' in client.get("/").text


# --- The precedent switch from the API --------------------------------------------------------------------------------------


def test_a_run_started_with_precedent_on_serves_precedents_and_the_ruling_cites_one(client):
    case_id = client.post("/api/disputes/DISP-003/run?precedent=true").json()["case_id"]
    for _ in range(100):
        body = client.get(f"/api/cases/{case_id}").json()
        if body["case"]["outcomes"]:
            break
        time.sleep(0.05)

    assert body["case"]["switches"]["policy_precedent"] is True
    assert [p["precedent_id"] for p in body["case"]["precedents"]]
    assert body["case"]["ruling"]["cited_precedent_ids"] == ["PREC-NS-02"]
    assert any(event["kind"] == "precedent_retrieved" for event in body["log"])


def test_a_run_started_without_the_switch_has_no_precedents(client):
    body = client.get(f"/api/cases/{run_and_wait(client, 'DISP-003')}").json()

    assert body["case"]["switches"]["policy_precedent"] is False and body["case"]["precedents"] == []
