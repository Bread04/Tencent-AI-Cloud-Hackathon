"""Filing a Dispute from the report form: the form's report becomes a Dispute, and the API runs it on the stub."""

import time
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.api.demo import ReplayModel
from src.contracts import CaseStatus, DisputeCategory, Party
from src.intake import load_catalog
from src.intake.report import ReportError, dispute_from_report
from src.store import CaseStore

TRIP = "TRIP-2026-09945"  # the trip behind prepared DISP-002


def a_report(**overrides):
    """A report as the form produces it (prototypes/ryde-report)."""
    report = {
        "id": "DEMO-20261013-ABC123",
        "createdAt": "2026-10-13T08:00:00.000Z",
        "demo": True,
        "reporterRole": "Rider",
        "trip": {"reference": TRIP, "date": "2026-09-13", "details": "Tiong Bahru Plaza → VivoCity", "simulatedSourceTrip": True},
        "category": "No-show / cancellation",
        "summary": "Dispute of SGD 5.00 no-show cancellation fee",
        "statement": "I waited at the lobby and the driver never came. Please reverse the fee.",
        "incident": {"time": "2026-09-13T08:45", "timeUnknown": False, "timeZone": "Asia/Singapore", "location": "Tiong Bahru Plaza"},
        "categoryDetails": {"situation": "A no-show / cancellation fee was charged", "waiting": "10"},
        "requestedResolution": {"type": "Refund", "amount": 5, "currency": "SGD"},
        "evidence": [],
        "confirmation": "Accurate to the best of my knowledge",
    }
    return report | overrides


def catalog():
    return load_catalog()


def test_a_report_becomes_a_dispute_that_keeps_the_report_unchanged():
    report = a_report()
    original = deepcopy(report)

    dispute = dispute_from_report(report, catalog())

    assert report == original and dispute.filed_report == original
    assert dispute.trip_id == TRIP and dispute.filed_by is Party.RIDER
    assert dispute.category is DisputeCategory.NO_SHOW_CHARGE
    assert dispute.description == report["statement"]
    assert dispute.incident.time_zone == "Asia/Singapore" and dispute.incident.location == "Tiong Bahru Plaza"
    assert dispute.category_details == {"situation": "A no-show / cancellation fee was charged", "waiting": "10"}
    assert (dispute.requested_resolution.type, str(dispute.requested_resolution.amount), dispute.requested_resolution.currency) == ("Refund", "5", "SGD")
    assert "5" in dispute.requested_remedy and "Refund" in dispute.requested_remedy


def test_the_dispute_id_comes_from_the_report_id_and_never_collides_with_a_prepared_one():
    dispute = dispute_from_report(a_report(), catalog())
    assert dispute.dispute_id == "DISP-DEMO-20261013-ABC123"
    assert dispute.dispute_id not in catalog().disputes


def test_a_driver_report_is_filed_by_the_driver_and_an_unknown_time_stays_unknown():
    report = a_report(reporterRole="Driver", incident={"time": None, "timeUnknown": True, "timeZone": "Asia/Singapore", "location": ""})
    dispute = dispute_from_report(report, catalog())
    assert dispute.filed_by is Party.DRIVER
    assert dispute.incident.time is None and dispute.incident.location is None


@pytest.mark.parametrize("category, expected", [
    ("Route deviation", DisputeCategory.ROUTE_DEVIATION),
    ("Damage / mess", DisputeCategory.PROPERTY_DAMAGE),
    ("Safety / conduct", DisputeCategory.SAFETY_INCIDENT),
])
def test_each_form_category_that_the_workflow_handles_maps_to_a_dispute_category(category, expected):
    assert dispute_from_report(a_report(category=category), catalog()).category is expected


@pytest.mark.parametrize("category", ["Fare / payment", "Lost item", "Other", "Made up"])
def test_a_category_the_workflow_cannot_resolve_is_rejected_with_the_supported_ones_named(category):
    with pytest.raises(ReportError, match="cannot be resolved yet") as error:
        dispute_from_report(a_report(category=category), catalog())
    assert category in str(error.value) and "No-show / cancellation" in str(error.value)


def test_an_unknown_trip_is_rejected_by_name():
    report = a_report(trip={"reference": "TRIP-NOPE"})
    with pytest.raises(ReportError, match="TRIP-NOPE"):
        dispute_from_report(report, catalog())


@pytest.mark.parametrize("change, message", [
    ({"id": ""}, "report ID"),
    ({"statement": "  "}, "statement"),
    ({"reporterRole": "Admin"}, "Rider or Driver"),
    ({"requestedResolution": {"type": "Refund", "amount": -1, "currency": "SGD"}}, "requested"),
    ({"requestedResolution": {"type": "Refund", "amount": 5}}, "requested"),
    ({"incident": {"time": "yesterday", "timeZone": "Asia/Singapore"}}, "incident"),
    ({"categoryDetails": "waited"}, "category details"),
])
def test_a_malformed_report_is_rejected_with_the_field_named(change, message):
    with pytest.raises(ReportError, match=message):
        dispute_from_report(a_report(**change), catalog())


@pytest.fixture
def client(monkeypatch):
    store = CaseStore()
    app = create_app(store=store, model=ReplayModel(store, catalog=catalog()), catalog=catalog())
    return TestClient(app), store


def finished(client, case_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        body = client.get(f"/api/cases/{case_id}").json()
        if body["case"]["status"] not in {"filed", "prioritised", "gathering_evidence", "building_cases", "judging"}:
            return body
        time.sleep(0.02)
    raise AssertionError("the run did not finish")


def test_filing_a_report_creates_a_case_and_runs_it_on_the_stub_with_the_report_kept_as_filed(client):
    http, store = client
    report = a_report()

    response = http.post("/api/reports", json=report)

    assert response.status_code == 202
    body = finished(http, response.json()["case_id"])
    assert body["case"]["status"] in {CaseStatus.RULED, CaseStatus.NOTIFIED, CaseStatus.PENDING_REVIEW, CaseStatus.CLOSED}
    assert body["case"]["ruling"] is not None and body["log"]
    assert body["case"]["dispute"]["filed_report"] == report
    assert body["case"]["dispute"]["dispute_id"] == "DISP-DEMO-20261013-ABC123"
    assert body["run_error"] is None


def test_a_report_for_an_unknown_trip_is_refused_before_any_case_exists(client):
    http, store = client
    response = http.post("/api/reports", json=a_report(trip={"reference": "TRIP-NOPE"}))
    assert response.status_code == 422 and "TRIP-NOPE" in response.json()["error"]
    assert store.list_cases() == []


def test_an_unsupported_category_is_refused_with_a_clear_error(client):
    http, store = client
    response = http.post("/api/reports", json=a_report(category="Lost item"))
    assert response.status_code == 422 and "Lost item" in response.json()["error"]
    assert store.list_cases() == []


def test_a_body_that_is_not_a_report_object_is_refused(client):
    http, _ = client
    assert http.post("/api/reports", content=b"[1, 2]", headers={"Content-Type": "application/json"}).status_code == 400
    assert http.post("/api/reports", content=b"not json", headers={"Content-Type": "application/json"}).status_code == 400
