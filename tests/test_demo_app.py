"""The demo entry point: the page wired to the prepared mock Disputes and the scripted stub, ready to run."""

from fastapi.testclient import TestClient

from src.api.demo import create_demo_app

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


def run_demo_dispute(dispute_id):
    import time

    client = TestClient(create_demo_app())
    case_id = client.post(f"/api/disputes/{dispute_id}/run").json()["case_id"]
    for _ in range(100):
        body = client.get(f"/api/cases/{case_id}").json()
        if body["case"]["outcomes"]:
            return body["case"]
        time.sleep(0.05)
    raise AssertionError("the run did not finish")


def test_the_demo_app_replays_each_dispute_with_its_own_script_not_the_first_ones():
    upheld = run_demo_dispute("DISP-003")
    held = run_demo_dispute("DISP-004")

    assert upheld["ruling"]["outcome"] == "uphold" and upheld["ruling"]["amount"] == "5.00"
    assert held["ruling"]["status"] == "proposal" and held["status"] == "pending_review"
