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
