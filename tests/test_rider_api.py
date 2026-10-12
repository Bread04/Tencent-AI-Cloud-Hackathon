"""Trusted telemetry, bounded payloads and server-owned locked public logs."""

from copy import deepcopy
import json

from fastapi.testclient import TestClient
import pytest

from src.api.chat import CLIENT_COOKIE_NAME, COOKIE_NAME
from src.agents.rider.validation import MAX_REQUEST_BYTES
from tests.test_chat import setup
from tests.test_rider_agents import report, sample_report

BASE = "/api/rider/"


@pytest.mark.parametrize("case_id", [f"DISP-{number:03}" for number in (2, 3, 4, 8, 9, 10)])
def test_case_api_prepares_redacted_scoped_python_result_and_real_locked_log(setup, case_id):
    app, client, _, model = setup
    trip, source = sample_report(case_id)
    response = client.post(BASE + "cases", json={"riderId": trip["riderId"], "report": source})
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    result = response.json()
    assert result["original_report"] == source and result["communication_log"] == [] and result["evidence"]["log"] == []
    assert result["submission"]["rider_statement"] == source["statement"]
    assert "intake_validated" not in response.text and "evidence_requested" not in response.text
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=strict" in response.headers["set-cookie"]
    path = "/api/rider-chat/transcripts/" + result["transcript_handle"]
    assert client.get(path).status_code == 403
    assert client.post(path + "/unlock", json={"code": "482731"}).status_code == 204
    unlocked = client.get(path).json()
    kinds = [entry["kind"] for entry in unlocked["communication_log"]]
    assert kinds.index("evidence_returned") < kinds.index("policy_retrieved") < kinds.index("submission_prepared")
    assert unlocked["context"] == result["context"]
    assert model.calls == []
    stranger = TestClient(app)
    stranger.cookies.set(COOKIE_NAME, client.cookies.get(COOKIE_NAME))
    assert stranger.get(path).status_code == 403
    assert stranger.post(path + "/unlock", json={"code": "482731"}).status_code == 403
    assert client.post(path + "/lock").status_code == 204 and client.get(path).status_code == 403


def test_standalone_evidence_has_same_gate_missing_report_and_reuses_owner_cookie(setup):
    _, client, _, _ = setup
    response = client.post(BASE + "evidence", json={"riderId": "R-7823", "tripId": "TRIP-2026-09945"})
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    result = response.json()
    assert result["log"] == [] and "evidence_request" not in response.text
    assert next(item for item in result["items"] if item["source"] == "rider_app.report")["status"] == "missing"
    owner = client.cookies.get(CLIENT_COOKIE_NAME)
    path = "/api/rider-chat/transcripts/" + result["transcript_handle"]
    assert client.get(path).status_code == 403
    client.post(path + "/unlock", json={"code": "482731"})
    assert all(entry["agent"] == "Rider Evidence Agent" for entry in client.get(path).json()["communication_log"])
    again = client.post(BASE + "cases", json={"riderId": "R-7823", "report": report()}).json()
    assert again["transcript_handle"] != result["transcript_handle"]
    assert client.cookies.get(CLIENT_COOKIE_NAME) == owner


def test_policy_preview_is_informational_and_does_not_register_transcript(setup):
    _, client, _, model = setup
    draft = report()
    for key in ("id", "createdAt", "demo", "confirmation"):
        del draft[key]
    response = client.post(BASE + "policy-preview", json={"report": draft})
    assert response.status_code == 200 and response.json()["status"] == "matched"
    assert "transcript_handle" not in response.text and client.cookies.get(CLIENT_COOKIE_NAME) is None
    assert model.calls == []
    assert client.post(BASE + "policy-preview", json={"report": report(reporterRole="Driver")}).status_code == 400


@pytest.mark.parametrize("path,payload", [
    ("cases", {"riderId": "R-DEMO-02", "report": report()}),
    ("cases", {"riderId": "R-7823", "report": report(reporterRole="Driver")}),
    ("cases", {"riderId": "R-7823", "report": report(), "evidence": {"paid_net": "999"}}),
    ("cases", {"riderId": None, "report": report()}),
    ("cases", {"riderId": "R-7823", "report": {"trip": []}}),
    ("cases", {"riderId": "R-7823", "report": report(evidence=[{"caption": []}])}),
    ("evidence", {"riderId": "R-DEMO-02", "tripId": "TRIP-2026-09945"}),
    ("evidence", {"riderId": "unknown", "tripId": "TRIP-2026-09945"}),
    ("evidence", {"riderId": "R-7823", "tripId": "TRIP-2026-09945", "report": report(trip={"reference": "elsewhere"})}),
    ("evidence", {"riderId": "R-7823", "tripId": "TRIP-2026-09945", "routeRecord": {}}),
    ("evidence", {"riderId": "R-7823", "tripId": "TRIP-2026-09945", "report": []}),
    ("policy-preview", {"report": report(categoryDetails={"nested": {"value": "bad"}})}),
    ("policy-preview", {"report": report(), "policy": {"clauses": []}}),
])
def test_malformed_cross_owner_driver_and_client_evidence_payloads_fail_without_log_or_cookie(setup, path, payload):
    _, client, _, model = setup
    response = client.post(BASE + path, json=payload)
    assert response.status_code == 400
    assert "communication_log" not in response.text and "transcript_handle" not in response.text
    assert client.cookies.get(CLIENT_COOKIE_NAME) is None and model.calls == []


@pytest.mark.parametrize("body", [b"{broken", b"\xff", b"x" * (MAX_REQUEST_BYTES + 1), b'{"report":NaN}', b'{"report":Infinity}', b'{"report":1e999}', b'{"report":{},"report":{}}', b"[" * 1000 + b"0" + b"]" * 1000, b'{"report":{"statement":"\\ud800"}}'], ids=["broken", "utf8", "oversize", "nan", "infinity", "overflow", "duplicate", "deep", "surrogate"])
def test_bounded_invalid_json_returns_controlled_error(setup, body):
    _, client, _, _ = setup
    response = client.post(BASE + "policy-preview", content=body)
    assert response.status_code == 400 and client.cookies.get(CLIENT_COOKIE_NAME) is None


def test_unsupported_categories_are_redacted_and_capacity_fails_visibly(setup):
    app, client, _, _ = setup
    response = client.post(BASE + "cases", json={"riderId": "R-7823", "report": report(category="Lost item")})
    assert response.status_code == 200 and response.json()["status"] == "support_required"
    assert response.json()["communication_log"] == [] and "submission" not in response.json()
    app.state.rider_transcripts.max_records = 0
    response = client.post(BASE + "cases", json={"riderId": "R-7823", "report": report()})
    assert response.status_code == 503 and "communication_log" not in response.text
