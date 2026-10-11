"""Seam: the bare page. Pick a prepared Dispute, run it, see the Ruling and the Communication Log."""

from html import escape

import pytest
from fastapi.testclient import TestClient

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
