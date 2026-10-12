"""Seams: model_from_environment(env, stub) and run_dispute when the model fails. A dead model must never produce a made-up Ruling."""

import pytest

from src.contracts import CaseStatus, LogEventKind
from src.intake import load_catalog
from src.llm import ModelError
from src.llm.client import OpenAICompatibleModel
from src.llm.factory import ModelNotConfigured, model_from_environment
from src.orchestrator import run_dispute
from src.store import CaseStore

from tests.cases import DISPUTE_ID, a_stub_for

REAL = {"MODEL_PROVIDER": "openai_compatible", "MODEL_BASE_URL": "https://models.example/v1", "MODEL_API_KEY": "sk-x", "MODEL_NAME": "m"}


# --- One setting switches the stub and the real model ----------------------------------------------------------


def test_with_no_setting_the_stub_is_used():
    stub = a_stub_for("CASE-0001")

    assert model_from_environment({}, stub=stub) is stub


def test_the_stub_can_be_named_explicitly():
    stub = a_stub_for("CASE-0001")

    assert model_from_environment({"MODEL_PROVIDER": "stub"}, stub=stub) is stub


def test_one_setting_switches_to_the_real_model():
    model = model_from_environment(REAL, stub=a_stub_for("CASE-0001"))

    assert isinstance(model, OpenAICompatibleModel)


@pytest.mark.parametrize("missing", ["MODEL_BASE_URL", "MODEL_API_KEY", "MODEL_NAME"])
def test_the_real_model_without_its_credentials_says_which_one_is_missing(missing):
    env = {key: value for key, value in REAL.items() if key != missing}

    with pytest.raises(ModelNotConfigured, match=missing):
        model_from_environment(env, stub=a_stub_for("CASE-0001"))


def test_an_unknown_provider_is_refused_rather_than_silently_stubbed():
    with pytest.raises(ModelNotConfigured, match="MODEL_PROVIDER"):
        model_from_environment({"MODEL_PROVIDER": "gpt-nine"}, stub=a_stub_for("CASE-0001"))


# --- Visible failure ----------------------------------------------------------------------------------------------


class DeadModel:
    """A model that is unreachable on every call."""

    def complete(self, messages, *, case_id, agent, schema=None, images=None):
        raise ModelError("The model could not be reached at https://models.example/v1/chat/completions (ConnectError).")


class DeadJudge:
    """The advocates answer from the script; the Judge's model is unreachable."""

    def __init__(self, stub):
        self._stub = stub

    def complete(self, messages, *, case_id, agent, schema=None, images=None):
        if agent.startswith("judge"):
            raise ModelError("The model timed out after 30 seconds (agent judge).")
        return self._stub.complete(messages, case_id=case_id, agent=agent, schema=schema, images=images)


def run_with(model):
    catalog, store = load_catalog(), CaseStore()
    case = run_dispute(catalog.dispute(DISPUTE_ID), store=store, model=model, catalog=catalog)
    return store, case


def test_an_unreachable_model_holds_the_case_for_review_with_the_reason_and_no_ruling():
    store, case = run_with(DeadModel())

    assert case.status is CaseStatus.PENDING_REVIEW
    assert case.ruling is None  # never a made-up Ruling
    escalation = [event for event in store.log(case.case_id) if event.kind is LogEventKind.ESCALATED]
    assert "could not be reached" in escalation[0].summary
    assert {outcome.action_status.value for outcome in case.outcomes} == {"pending_review"}


def test_a_judge_that_times_out_after_the_advocates_filed_still_ends_in_review_with_their_submissions_kept():
    _, case = run_with(DeadJudge(a_stub_for("CASE-0001")))

    assert case.status is CaseStatus.PENDING_REVIEW
    assert case.ruling is None
    assert len(case.submissions) == 2  # work already done is not thrown away
