"""Seam: the Demo Day console's JSON API and static files. The page's own behaviour is checked in a browser."""

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.contracts import Case, LogEvent
from src.intake import load_catalog
from src.store import CaseStore

from tests.cases import DISPUTE_ID, a_stub_for

RECORDED = Path(__file__).resolve().parents[1] / "src" / "api" / "static" / "recorded"


@pytest.fixture
def client():
    app = create_app(store=CaseStore(), model=a_stub_for("CASE-0001"), catalog=load_catalog())
    return TestClient(app)


def run_and_wait(client, dispute_id=DISPUTE_ID):
    started = client.post(f"/api/disputes/{dispute_id}/run")
    case_id = started.json()["case_id"]
    for _ in range(100):
        body = client.get(f"/api/cases/{case_id}").json()
        if body["case"]["outcomes"]:
            return case_id, body
        time.sleep(0.05)
    raise AssertionError("the run did not finish")


def test_starting_a_run_returns_the_case_id_at_once_and_the_case_can_be_read_while_it_runs(client):
    started = client.post(f"/api/disputes/{DISPUTE_ID}/run")

    assert started.status_code == 202
    assert started.json()["case_id"] == "CASE-0001"
    assert client.get("/api/cases/CASE-0001").status_code == 200


def test_the_case_json_carries_what_the_console_shows_the_ruling_evidence_clauses_outcomes_and_log(client):
    _, body = run_and_wait(client)

    case = Case.model_validate(body["case"])
    log = [LogEvent.model_validate(event) for event in body["log"]]
    assert case.ruling.confidence.components
    assert case.evidence and case.policy_clauses and len(case.outcomes) == 2
    assert [event.timestamp for event in log] == sorted(event.timestamp for event in log)  # oldest first


def test_a_dispute_that_does_not_exist_is_a_clear_404_in_the_api_too(client):
    response = client.post("/api/disputes/DISP-NOPE/run")

    assert response.status_code == 404
    assert "DISP-NOPE" in response.json()["error"]


def test_a_case_that_does_not_exist_is_a_clear_404_in_the_api_too(client):
    response = client.get("/api/cases/CASE-9999")

    assert response.status_code == 404
    assert "CASE-9999" in response.json()["error"]


def test_the_home_page_is_the_console_and_labels_everything_as_simulated(client):
    page = client.get("/").text

    assert "console.js" in page and "console.css" in page
    assert "mock data" in page.lower() and "simulated" in page.lower()
    for dispute_id in load_catalog().disputes:
        assert dispute_id in page


@pytest.mark.parametrize(
    "path",
    [
        "/static/console.js",
        "/static/console.css",
        "/prototypes/shared/waypoint.css",
        "/prototypes/ryde-app/styles.css",
        "/prototypes/shared/fonts/nunito-variable.ttf",
        "/prototypes/shared/waypoint-mark.svg",
    ],
)
def test_the_console_and_the_rider_apps_own_styles_are_served(client, path):
    assert client.get(path).status_code == 200


def test_the_console_loads_the_rider_apps_stylesheets_so_it_looks_like_the_rider_app(client):
    page = client.get("/").text

    for sheet in ("ryde-app/styles.css", "shared/waypoint.css", "shared/experience.css"):
        assert sheet in page


@pytest.mark.parametrize("dispute_id", sorted(load_catalog().disputes))
def test_every_prepared_dispute_has_a_recorded_stream_the_console_can_replay_without_the_orchestrator(dispute_id):
    body = json.loads((RECORDED / f"{dispute_id}.json").read_text(encoding="utf-8"))

    case = Case.model_validate(body["case"])
    assert case.dispute.dispute_id == dispute_id
    assert case.ruling is not None or case.outcomes  # a ruled or held Case, never empty
    assert body["log"]


def test_the_console_is_told_the_escalation_threshold_so_the_confidence_gauge_marks_the_real_line(client):
    from src.config import CONFIG

    page = client.get("/").text

    assert f'data-threshold="{CONFIG.escalation.confidence_threshold}"' in page


def test_the_console_says_it_is_running_on_scripted_replies_by_default(client):
    assert "Scripted replies" in client.get("/").text


def test_the_console_names_the_live_model_when_one_is_in_use():
    app = create_app(store=CaseStore(), model=a_stub_for("CASE-0001"), catalog=load_catalog(), model_label="Live model: some/model:free")

    assert "Live model: some/model:free" in TestClient(app).get("/").text
