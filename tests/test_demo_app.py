"""The demo entry point: the page wired to the prepared mock Disputes and the scripted stub, ready to run."""

from fastapi.testclient import TestClient
from decimal import Decimal
from pathlib import Path

import pytest

from src.contracts import citation_errors
from src.api import create_app
from src.api.demo import ReplayModel, create_demo_app
from src.intake import load_catalog
from src.llm.adapter import ModelError
from src.store import CaseStore

from tests.cases import DISPUTE_ID, stub_replies


def test_the_demo_app_runs_a_prepared_dispute_without_any_setup():
    client = TestClient(create_demo_app())

    page = client.post(f"/disputes/{DISPUTE_ID}/run", follow_redirects=True)

    assert page.status_code == 200
    assert "Communication Log" in page.text
    assert "CASE-0001" in page.text


def test_the_demo_app_can_run_the_same_dispute_more_than_once():
    client = TestClient(create_demo_app())

    client.post(f"/disputes/{DISPUTE_ID}/run")
    second = client.post(f"/disputes/{DISPUTE_ID}/run", follow_redirects=True)

    assert "CASE-0002" in second.text
    assert stub_replies()["judge"]["reasoning_summary"].split(".")[0] in second.text


def test_mixed_demo_runs_keep_their_submissions_rulings_and_stored_pages_independent():
    store = CaseStore()
    model = ReplayModel(store)
    client = TestClient(create_app(store=store, model=model, catalog=load_catalog()))
    pages = []
    for dispute_id in ["DISP-004", "DISP-003", "DISP-002", "DISP-004"]:
        page = client.post(f"/disputes/{dispute_id}/run", follow_redirects=True)
        assert page.status_code == 200
        case = store.list_cases()[-1]
        assert case.dispute.dispute_id == dispute_id
        replies = stub_replies(dispute_id)
        assert [s.claim_restated for s in case.submissions] == [
            replies[agent]["claim_restated"] for agent in ["rider_advocate", "driver_advocate"]
        ]
        assert case.ruling.reasoning_summary == replies["judge"]["reasoning_summary"]
        assert case.evidence_version == f"{case.case_id}-evidence-v1"
        for document in [*case.submissions, case.ruling]:
            assert citation_errors(document, case.evidence, case.policy_clauses, case.precedents) == []
        assert all(item.trip_id == case.dispute.trip_id for item in case.evidence)
        assert {event.case_id for event in store.log(case.case_id)} == {case.case_id}
        assert {outcome.party.value for outcome in case.outcomes} == {"rider", "driver"}
        expected_action = "pending_review" if dispute_id == "DISP-004" else "recommended"
        assert all(outcome.action_status == expected_action for outcome in case.outcomes)
        assert "Simulated" in page.text

        if dispute_id == "DISP-003":
            assert case.status == "notified"
            assert case.ruling.status == "final"
            assert case.ruling.outcome == "uphold"
            assert case.ruling.remedy == "fee_reversal"
            fare = next(item for item in case.evidence if item.source == "fare")
            assert case.ruling.amount == Decimal(fare.derived["cancellation_fee"]) == Decimal("5.00")
            assert case.ruling.calculation.result == case.ruling.amount
            assert case.ruling.calculation.input_evidence_ids == [fare.evidence_id]
            assert all("four-minute" in s.claim_restated for s in case.submissions)
            assert "SGD 5.00" in page.text
        elif dispute_id == "DISP-004":
            assert case.status == "pending_review"
            assert case.ruling.status == "proposal"
            assert case.ruling.balance_of_evidence == "balanced"
            assert case.ruling.policy_fit == "unclear"
            assert case.ruling.confidence.value == 0.5
            assert [record.trigger for record in case.ruling.review_triggers] == ["balanced_evidence", "policy_gap", "low_confidence"]
            assert all("09:02" in s.claim_restated for s in case.submissions)
            assert "no final decision" in page.text.lower()
            assert "No payment is authorized or executed" in page.text
            assert "balanced_evidence" in page.text and "pending_review" in page.text
            assert "Outcome:" not in page.text and "Amount:" not in page.text
            assert case.ruling.amount is None
        else:
            assert case.status == "notified"
            assert case.ruling.status == "final"
            assert case.ruling.outcome == "reject"
            assert case.ruling.remedy == "no_action"
            assert not case.ruling.review_triggers
        pages.append((page.url.path, page.text))

    assert len(model.calls) == 16
    for path, original in pages:
        assert client.get(path).text == original
    assert len(model.calls) == 16


def test_a_stored_dispute_without_a_prepared_script_has_a_clear_model_error():
    store = CaseStore()
    dispute = load_catalog().dispute("DISP-003").model_copy(update={"dispute_id": "DISP-UNSCRIPTED"})
    case = store.create_case(dispute)
    model = ReplayModel(store)

    with pytest.raises(ModelError, match="no prepared script for dispute DISP-UNSCRIPTED"):
        model.complete([], case_id=case.case_id, agent="rider_advocate")


def test_a_prepared_script_missing_an_agent_has_a_clear_model_error_without_fallback():
    store = CaseStore()
    case = store.create_case(load_catalog().dispute("DISP-003"))
    scripts = {dispute_id: stub_replies(dispute_id) for dispute_id in ["DISP-002", "DISP-003"]}
    del scripts["DISP-003"]["driver_advocate"]
    model = ReplayModel(store, scripts)

    with pytest.raises(ModelError, match="dispute DISP-003, agent driver_advocate"):
        model.complete([], case_id=case.case_id, agent="driver_advocate")


def test_list_replies_are_consumed_independently_for_each_case():
    store = CaseStore()
    dispute = load_catalog().dispute("DISP-003")
    first, second = (store.create_case(dispute).case_id for _ in range(2))
    model = ReplayModel(store, {"DISP-003": {"judge": ["first", "second"]}})

    assert model.complete([], case_id=first, agent="judge") == "first"
    assert model.complete([], case_id=second, agent="judge") == "first"
    assert model.complete([], case_id=first, agent="judge") == "second"
    assert model.complete([], case_id=second, agent="judge") == "second"
    with pytest.raises(ModelError, match="used up"):
        model.complete([], case_id=first, agent="judge")


def test_demo_catalog_and_replay_never_read_evaluation_files(monkeypatch):
    read_text = Path.read_text
    reads = []

    def guarded_read(path, *args, **kwargs):
        assert not path.name.endswith(".eval.json")
        reads.append(path)
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read)
    client = TestClient(create_demo_app())
    for dispute_id in ["DISP-002", "DISP-003", "DISP-004"]:
        assert client.post(f"/disputes/{dispute_id}/run").status_code == 200
    assert any(path.parent.name == "stub" for path in reads)
    assert any(path.parent.name == "cases" for path in reads)
