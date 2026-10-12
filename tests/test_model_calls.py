"""Seam: every model call is recorded (who asked, what was sent, what came back, how long) and shows in the Communication Log."""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from src.api.demo import create_demo_app
from src.contracts import LogEventKind
from src.intake import load_catalog
from src.llm import ModelError, StubModel
from src.llm.recording import RecordingModel
from src.llm.repair import feedback_message
from src.orchestrator import run_dispute
from src.store import CaseStore

from tests.builders import a_dispute
from tests.cases import a_stub_for, stub_replies


class Answer(BaseModel):
    text: str


def a_recorded(script):
    store = CaseStore()
    case = store.create_case(a_dispute())
    return store, case.case_id, RecordingModel(StubModel({(case.case_id, "judge"): script}), store)


ASK = [{"role": "system", "content": "Rule."}, {"role": "user", "content": "Case facts."}]


def test_a_call_is_passed_through_and_recorded_with_what_was_sent_and_what_came_back():
    store, case_id, model = a_recorded({"text": "hello"})

    reply = model.complete(ASK, case_id=case_id, agent="judge", schema=Answer)

    assert reply == Answer(text="hello")
    (call,) = store.calls(case_id)
    assert (call.agent, call.attempt, call.outcome) == ("judge", 1, "ok")
    assert call.messages == ASK and "hello" in call.reply
    assert call.seconds >= 0 and call.model == "scripted replies"
    event = store.log(case_id)[-1]
    assert event.kind is LogEventKind.MODEL_CALL and event.agent == "judge" and "call 1" in event.summary.lower()


def test_a_second_call_that_carries_feedback_is_a_retry_and_says_why_it_was_sent_back():
    store, case_id, model = a_recorded([{"text": "one"}, {"text": "two"}])
    model.complete(ASK, case_id=case_id, agent="judge", schema=Answer)

    model.complete([*ASK, feedback_message(["EV-NOPE-1 is cited but does not exist."])], case_id=case_id, agent="judge", schema=Answer)

    first, second = store.calls(case_id)
    assert (second.attempt, second.sent_back_because is not None) == (2, True)
    assert "EV-NOPE-1" in second.sent_back_because
    assert first.sent_back_because is None
    assert "sent back" in store.log(case_id)[-1].summary and "EV-NOPE-1" in store.log(case_id)[-1].summary


def test_an_unreachable_model_is_recorded_as_failed_and_the_error_still_surfaces():
    store = CaseStore()
    case_id = store.create_case(a_dispute()).case_id

    class Dead:
        def complete(self, messages, *, case_id, agent, schema=None, images=None):
            raise ModelError("The model timed out after 30 seconds (agent judge).")

    with pytest.raises(ModelError):
        RecordingModel(Dead(), store).complete(ASK, case_id=case_id, agent="judge")

    (call,) = store.calls(case_id)
    assert call.outcome == "failed" and "timed out" in call.problem
    assert "failed" in store.log(case_id)[-1].summary


def test_a_reply_that_breaks_the_schema_is_recorded_as_invalid_and_the_error_still_surfaces():
    store, case_id, model = a_recorded({"wrong": "shape"})

    with pytest.raises(ValidationError):
        model.complete(ASK, case_id=case_id, agent="judge", schema=Answer)

    assert store.calls(case_id)[0].outcome == "invalid"


# --- In a whole run --------------------------------------------------------------------------------------------------


def run(dispute_id="DISP-003"):
    catalog, store = load_catalog(), CaseStore()
    case = run_dispute(catalog.dispute(dispute_id), store=store, model=a_stub_for("CASE-0001", dispute_id), catalog=catalog)
    return store, case


def test_a_run_records_every_call_by_every_agent():
    store, case = run()

    assert {call.agent for call in store.calls(case.case_id)} == {"rider_advocate", "driver_advocate", "judge", "judge_self_check"}
    assert [e for e in store.log(case.case_id) if e.kind is LogEventKind.MODEL_CALL]


def test_the_judge_logs_its_verdict_on_each_argument_with_the_evidence_it_turned_on():
    store, case = run("DISP-002")

    events = [e for e in store.log(case.case_id) if e.kind is LogEventKind.ARGUMENT_ASSESSED]

    assert len(events) == len(case.ruling.argument_assessments) == 4
    assert all(e.agent == "judge" and e.references for e in events)
    assert any("unproven" in e.summary for e in events)


def test_a_bad_citation_is_sent_back_and_both_attempts_show():
    replies = stub_replies("DISP-003")
    bad = {**replies["rider_advocate"], "facts_relied_on": ["EV-NOPE-1"]}
    script = {(("CASE-0001"), "rider_advocate"): [bad, replies["rider_advocate"]], ("CASE-0001", "driver_advocate"): replies["driver_advocate"],
              ("CASE-0001", "judge"): replies["judge"], ("CASE-0001", "judge_self_check"): replies["judge_self_check"]}
    catalog, store = load_catalog(), CaseStore()

    case = run_dispute(catalog.dispute("DISP-003"), store=store, model=StubModel(script), catalog=catalog)

    rider = [c for c in store.calls(case.case_id) if c.agent == "rider_advocate"]
    assert [c.attempt for c in rider] == [1, 2]
    assert "EV-NOPE-1" in rider[1].sent_back_because
    assert case.ruling is not None  # the retry fixed it


def test_the_api_returns_the_calls_with_their_prompts_and_replies():
    client = TestClient(create_demo_app())
    case_id = client.post("/api/disputes/DISP-003/run").json()["case_id"]
    import time

    for _ in range(100):
        body = client.get(f"/api/cases/{case_id}").json()
        if body["case"]["outcomes"]:
            break
        time.sleep(0.05)

    judge = next(call for call in body["calls"] if call["agent"] == "judge")
    assert judge["messages"] and judge["reply"] and judge["outcome"] == "ok"
