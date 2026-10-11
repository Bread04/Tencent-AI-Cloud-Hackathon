"""Seam: the bare page. Pick a prepared Dispute, run it, see the Ruling and the Communication Log."""

from html import escape

import pytest
from fastapi.testclient import TestClient

from src.agents.policy import SIMULATED_LABEL
from src.api import create_app
from src.intake import load_catalog
from src.store import CaseStore

from tests.cases import DISPUTE_ID, a_stub_for


@pytest.fixture
def store():
    return CaseStore()


@pytest.fixture
def client(store):
    app = create_app(store=store, model=a_stub_for("CASE-0001"), catalog=load_catalog())
    return TestClient(app)


def test_the_home_page_lists_the_prepared_disputes_and_says_they_are_simulated(client):
    page = client.get("/")

    assert page.status_code == 200
    assert DISPUTE_ID in page.text
    assert "simulated" in page.text.lower()


def test_running_a_prepared_dispute_shows_the_ruling_and_the_log_in_order(client, store):
    page = client.post(f"/disputes/{DISPUTE_ID}/run", follow_redirects=True)

    case = store.get_case("CASE-0001")
    assert page.status_code == 200
    assert escape(case.ruling.reasoning_summary) in page.text
    assert case.ruling.outcome.value in page.text
    assert str(case.ruling.confidence.value) in page.text
    positions = [page.text.index(escape(event.summary)) for event in store.log("CASE-0001")]
    assert positions == sorted(positions)  # every log event is on the page, oldest first


def test_a_dispute_that_does_not_exist_is_a_clear_404(client):
    response = client.post("/disputes/DISP-NOPE/run")

    assert response.status_code == 404
    assert "DISP-NOPE" in response.text


def test_a_case_that_does_not_exist_is_a_clear_404(client):
    response = client.get("/cases/CASE-9999")

    assert response.status_code == 404
    assert "CASE-9999" in response.text


def test_the_case_page_shows_the_policy_clauses_cited_and_labels_the_policy_as_simulated(client, store):
    page = client.post(f"/disputes/{DISPUTE_ID}/run", follow_redirects=True)

    case = store.get_case("CASE-0001")
    assert escape(SIMULATED_LABEL) in page.text
    for clause in case.policy_clauses:
        assert clause.clause_id in page.text
        assert escape(clause.text) in page.text
    assert case.policy_clauses[0].version in page.text


def test_reopening_a_ruled_case_shows_the_stored_ruling_and_does_not_call_the_model_again(store):
    model = a_stub_for("CASE-0001")
    client = TestClient(create_app(store=store, model=model, catalog=load_catalog()))
    first = client.post(f"/disputes/{DISPUTE_ID}/run", follow_redirects=True)
    calls_after_the_run = len(model.calls)

    reopened = [client.get("/cases/CASE-0001") for _ in range(2)]

    assert len(model.calls) == calls_after_the_run
    assert all(page.text == first.text for page in reopened)
