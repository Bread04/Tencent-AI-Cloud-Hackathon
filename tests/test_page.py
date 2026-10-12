"""Seam: the bare page. Pick a prepared Dispute, run it, see the Ruling and the Communication Log."""

from html import escape
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.agents.policy import SIMULATED_LABEL
from src.api import create_app
from src.api.demo import ReplayModel
from src.intake import load_catalog
from src.store import CaseStore

from tests.cases import DISPUTE_ID, a_stub_for, stub_replies
from tests import builders as b


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
    start = 0
    for event in store.log("CASE-0001"):  # every log event is on the page, oldest first (some rows repeat their wording)
        start = page.text.index(escape(event.summary), start) + 1


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


def test_proposal_page_tolerates_absent_confidence_and_escapes_review_text(store, client):
    case_id = store.create_case(b.a_dispute()).case_id
    store.seal_evidence(case_id)
    store.add_submission(case_id, b.a_submission(author="rider_advocate"))
    store.add_submission(case_id, b.a_submission(author="driver_advocate"))
    store.set_ruling(case_id, b.a_ruling(
        status="proposal", confidence=None,
        reasoning_summary="Proposal <script>untrusted</script>",
        review_triggers=[{"trigger": "balanced_evidence", "reason": "Review <img src=x onerror=alert(1)>"}],
    ))

    page = client.get(f"/cases/{case_id}")

    assert page.status_code == 200
    assert "no final decision" in page.text
    assert "pending_review" in page.text
    assert "Confidence: not available" in page.text
    assert "Outcome:" not in page.text and "Amount:" not in page.text
    assert "No payment is authorized or executed" in page.text
    assert "&lt;script&gt;untrusted&lt;/script&gt;" in page.text
    review_list = page.text.split("<h3>Review reasons</h3><ul>", 1)[1].split("</ul>", 1)[0]
    for record in store.get_case(case_id).ruling.review_triggers:
        assert escape(record.trigger.value) in review_list
        assert escape(record.reason) in review_list
    assert "<script>" not in page.text and "<img" not in page.text


def test_fee_reversal_proposal_page_and_log_require_review_without_displaying_a_final_payment(store):
    replies = stub_replies("DISP-003")
    replies["judge"].update(policy_fit="unclear", policy_gap="No clause covers the disputed telemetry gap.")
    model = ReplayModel(store, {"DISP-003": replies})
    client = TestClient(create_app(store=store, model=model, catalog=load_catalog()))

    page = client.post("/disputes/DISP-003/run", follow_redirects=True)

    assert page.status_code == 200
    case = store.get_case("CASE-0001")
    ruling = case.ruling
    fare = next(item for item in case.evidence if item.source == "fare")
    assert case.status == "pending_review" and ruling.status == "proposal"
    assert ruling.outcome == "uphold" and ruling.remedy == "fee_reversal"
    assert ruling.amount == Decimal(fare.derived["cancellation_fee"])
    assert ruling.calculation.result == ruling.amount
    assert ruling.calculation.input_evidence_ids == [fare.evidence_id]
    assert [record.trigger for record in ruling.review_triggers] == ["policy_gap", "low_confidence"]
    assert len(case.outcomes) == 2
    assert all(outcome.action_status == "pending_review" for outcome in case.outcomes)

    review_list = page.text.split("<h3>Review reasons</h3><ul>", 1)[1].split("</ul>", 1)[0]
    for record in ruling.review_triggers:
        assert escape(record.trigger.value) in review_list
        assert escape(record.reason) in review_list
    assert "no final decision" in page.text
    assert "pending_review" in page.text
    assert "No payment is authorized or executed" in page.text
    assert "Outcome:" not in page.text and "Amount:" not in page.text
    assert "SGD 5.00" not in page.text
    summary = next(event.summary for event in store.log(case.case_id) if event.kind == "ruling_drafted")
    assert "Pending review" in summary
    assert "no final decision or payment authorization" in summary
    assert "low_confidence" in summary and "policy_gap" in summary
    assert "fee_reversal" not in summary and "5.00" not in summary
