"""The offline model stub: scripted replies per Case, no network."""

import socket

import pytest
from pydantic import ValidationError

from src.contracts import Submission
from src.llm import ModelError, StubModel
from tests import builders as b

MESSAGES = [{"role": "user", "content": "Build the rider's case."}]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the stub must not open a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def test_stub_returns_the_scripted_text_for_a_case_and_agent():
    model = StubModel({("CASE-0001", "rider_advocate"): "The driver never arrived."})

    reply = model.complete(MESSAGES, case_id="CASE-0001", agent="rider_advocate")

    assert reply == "The driver never arrived."


def test_stub_returns_a_schema_validated_object_when_a_schema_is_asked_for():
    scripted = b.a_submission().model_dump(mode="json")
    model = StubModel({("CASE-0001", "rider_advocate"): scripted})

    reply = model.complete(MESSAGES, case_id="CASE-0001", agent="rider_advocate", schema=Submission)

    assert reply == b.a_submission()


def test_stub_accepts_scripted_json_text_for_a_schema():
    model = StubModel({("CASE-0001", "rider_advocate"): b.a_submission().model_dump_json()})

    reply = model.complete(MESSAGES, case_id="CASE-0001", agent="rider_advocate", schema=Submission)

    assert isinstance(reply, Submission)


def test_different_cases_get_their_own_scripted_replies():
    model = StubModel(
        {
            ("CASE-0001", "judge"): "uphold",
            ("CASE-0002", "judge"): "reject",
        }
    )

    assert model.complete(MESSAGES, case_id="CASE-0002", agent="judge") == "reject"
    assert model.complete(MESSAGES, case_id="CASE-0001", agent="judge") == "uphold"


def test_a_list_of_replies_is_returned_one_per_call_in_order():
    model = StubModel({("CASE-0001", "judge"): ["first draft", "after self-check"]})

    assert model.complete(MESSAGES, case_id="CASE-0001", agent="judge") == "first draft"
    assert model.complete(MESSAGES, case_id="CASE-0001", agent="judge") == "after self-check"


def test_a_call_with_no_scripted_reply_fails_loudly_instead_of_making_one_up():
    model = StubModel({("CASE-0001", "judge"): ["only one"]})
    model.complete(MESSAGES, case_id="CASE-0001", agent="judge")

    with pytest.raises(ModelError) as unscripted_agent:
        model.complete(MESSAGES, case_id="CASE-0001", agent="driver_advocate")
    with pytest.raises(ModelError) as used_up:
        model.complete(MESSAGES, case_id="CASE-0001", agent="judge")

    assert "CASE-0001" in str(unscripted_agent.value) and "driver_advocate" in str(unscripted_agent.value)
    assert "CASE-0001" in str(used_up.value) and "judge" in str(used_up.value)


def test_a_scripted_reply_that_breaks_the_schema_raises_the_validation_error():
    broken = b.a_submission().model_dump(mode="json") | {"author": "judge"}
    model = StubModel({("CASE-0001", "rider_advocate"): broken})

    with pytest.raises(ValidationError) as error:
        model.complete(MESSAGES, case_id="CASE-0001", agent="rider_advocate", schema=Submission)

    assert "author" in str(error.value)


def test_stub_records_what_it_was_asked_so_tests_can_inspect_prompts():
    model = StubModel({("CASE-0001", "judge"): "uphold"})

    model.complete(MESSAGES, case_id="CASE-0001", agent="judge", images=["photo-1.jpg"])

    assert model.calls == [
        {"case_id": "CASE-0001", "agent": "judge", "messages": MESSAGES, "images": ["photo-1.jpg"], "schema": None}
    ]
