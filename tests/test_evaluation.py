"""Seam: evaluate(...) runs every mock case and compares the Ruling with its label. The labels are the harness's alone."""

import json

import pytest
from fastapi.testclient import TestClient

from src.api.demo import ReplayModel, create_demo_app
from src.config import CONFIG
from src.contracts import ArgumentVerdict, BalanceOfEvidence, Remedy, RulingOutcome, Switches
from src.evaluation import evaluate, load_labels, render_table
from src.intake import load_catalog

ROUTING = CONFIG.switches.model_copy(update={"sla_routing": True, "image_analysis": True})  # Safety Incidents need routing on; photo cases need photo analysis on


def run(factory=None, switches=ROUTING, labels=None, label="scripted replies"):
    made = []

    def model_for(store):
        model = (factory or ReplayModel)(store)
        made.append(model)
        return model

    report = evaluate(catalog=load_catalog(), model_for=model_for, switches=switches, model_label=label, labels=labels)
    return report, made


# --- One row per mock case --------------------------------------------------------------------------------------------------


def test_every_mock_case_gets_a_row_with_expected_and_actual_outcome_and_the_scripted_run_passes_them_all():
    report, _ = run()

    assert sorted(row.dispute_id for row in report.rows) == sorted(load_catalog().disputes)
    assert all(row.expected and row.actual for row in report.rows)
    assert (report.passed, report.total, report.rate) == (len(report.rows), len(report.rows), 1.0)


def test_the_rows_show_what_was_expected_and_what_happened_including_confidence():
    report, _ = run()
    rows = {row.dispute_id: row for row in report.rows}

    assert "uphold" in rows["DISP-003"].expected and "fee_reversal" in rows["DISP-003"].expected and "5.00" in rows["DISP-003"].expected
    assert "uphold" in rows["DISP-003"].actual and rows["DISP-003"].confidence == pytest.approx(0.8)
    assert "held for review" in rows["DISP-004"].expected and "held for review" in rows["DISP-004"].actual
    assert "held for review" in rows["DISP-005"].actual and "safety_incident" in rows["DISP-005"].actual


def test_the_report_says_which_model_produced_it():
    stub, _ = run(label="scripted replies")
    live, _ = run(label="Live model: some/model:free")

    assert stub.model == "scripted replies" and live.model == "Live model: some/model:free"
    assert "scripted replies" in render_table(stub) and "Live model: some/model:free" in render_table(live)


# --- The labels are the harness's alone ---------------------------------------------------------------------------------------


def test_no_agent_ever_sees_a_label():
    _, made = run()
    labels = load_labels()
    sent = json.dumps([call["messages"] for model in made for call in model.calls])

    for label in labels.values():
        assert label.expected_summary not in sent
    assert "expected_outcome" not in sent and "expected_remedy" not in sent and "acceptable_review_triggers" not in sent


def test_the_labels_are_read_after_the_case_is_ruled():
    order = []
    import src.evaluation as module

    real_load, real_run = module.load_labels, module.run_dispute
    module.run_dispute = lambda *a, **k: (order.append("run"), real_run(*a, **k))[1]
    labels = real_load()

    class Spy(dict):
        def __getitem__(self, key):
            order.append("label")
            return super().__getitem__(key)

        def get(self, key, default=None):
            order.append("label")
            return super().get(key, default)

    try:
        run(labels=Spy(labels))
    finally:
        module.run_dispute = real_run

    assert order.index("run") < order.index("label")  # the first Case was ruled before its label was looked at


# --- Regressions show as failures ---------------------------------------------------------------------------------------------


class FlippedJudge(ReplayModel):
    """A model that answers DISP-002 as if the rider had won: a regression in that case's outcome."""

    def complete(self, messages, *, case_id, agent, schema=None, images=None):
        result = super().complete(messages, case_id=case_id, agent=agent, schema=schema, images=images)
        if agent == "judge" and self._store.get_case(case_id).dispute.dispute_id == "DISP-002":
            claim_made_out = [a.model_copy(update={"verdict": ArgumentVerdict.ACCEPTED, "evidence_ids": ["EV-GPS-1"]}) if a.ref == "rider_advocate#claim" else a for a in result.argument_assessments]
            return result.model_copy(update={"outcome": RulingOutcome.UPHOLD, "remedy": Remedy.FEE_REVERSAL, "argument_assessments": claim_made_out,
                                             "balance_of_evidence": BalanceOfEvidence.CLAIMANT, "amount_input_evidence_ids": ["EV-FARE-1"]})
        return result


def test_a_wrong_outcome_in_any_case_shows_as_a_failure_and_lowers_the_pass_rate():
    report, _ = run(FlippedJudge)
    row = next(r for r in report.rows if r.dispute_id == "DISP-002")

    assert row.passed is False and report.passed == report.total - 1 and report.rate < 1.0
    assert "reject" in row.why and "uphold" in row.why


def test_an_ambiguous_case_that_is_ruled_without_review_fails():
    report, _ = run(switches=ROUTING.model_copy(update={"escalation": False}))
    row = next(r for r in report.rows if r.dispute_id == "DISP-004")

    assert row.passed is False and "review" in row.why


def test_a_case_that_is_turned_away_is_a_failure_with_the_reason():
    catalog, labels = load_catalog(), load_labels()
    catalog.disputes["DISP-X"] = catalog.disputes["DISP-002"].model_copy(update={"dispute_id": "DISP-X", "trip_id": "TRIP-NOPE"})  # a Dispute on a trip that does not exist
    labels["DISP-X"] = labels["DISP-002"]

    report = evaluate(catalog=catalog, model_for=ReplayModel, switches=ROUTING, model_label="scripted replies", labels=labels)
    row = next(r for r in report.rows if r.dispute_id == "DISP-X")

    assert row.passed is False and "turned away" in row.why


def test_a_case_with_no_label_is_a_failure_not_a_silent_skip():
    labels = load_labels()
    del labels["DISP-002"]

    report, _ = run(labels=labels)
    row = next(r for r in report.rows if r.dispute_id == "DISP-002")

    assert row.passed is False and "no expected-outcome label" in row.why


# --- The page ---------------------------------------------------------------------------------------------------------------------


@pytest.fixture
def client():
    return TestClient(create_demo_app())


def test_the_evaluation_page_shows_the_table_the_pass_rate_and_which_model_made_it(client):
    import time

    assert client.get("/api/evaluation").json()["state"] == "none"
    assert client.post("/api/evaluation/run").status_code == 202
    for _ in range(100):
        body = client.get("/api/evaluation").json()
        if body["state"] == "done":
            break
        time.sleep(0.1)

    assert body["report"]["model"] == "Scripted replies" and body["report"]["rate"] == 1.0
    page = client.get("/evaluation").text
    assert "evaluation.js" in page and "Evaluation" in page and "Scripted replies" in page


# --- A model that fails is not a wrong answer ------------------------------------------------------------------------------------------


class UnreachableModel:
    def complete(self, messages, *, case_id, agent, schema=None, images=None):
        from src.llm import ModelError

        raise ModelError("The model could not be reached at https://models.example/v1/chat/completions (ConnectError).")


def test_a_case_the_model_could_not_judge_is_reported_as_such_with_the_reason_not_as_a_wrong_outcome():
    report, _ = run(lambda store: UnreachableModel())
    row = next(r for r in report.rows if r.dispute_id == "DISP-003")

    assert row.judged is False and row.passed is False
    assert "could not be reached" in row.why and "wrong" not in row.why.lower()
    assert report.unjudged == report.total and report.passed == 0


def test_the_table_says_how_many_cases_could_not_be_judged_so_an_outage_is_not_read_as_bad_judgement():
    report, _ = run(lambda store: UnreachableModel())

    text = render_table(report)

    assert f"{report.total} could not be judged because the model failed" in text


def test_a_wrong_answer_is_still_judged():
    report, _ = run(FlippedJudge)

    assert next(r for r in report.rows if r.dispute_id == "DISP-002").judged is True
    assert report.unjudged == 0


def test_the_json_for_the_page_carries_the_unjudged_count():
    report, _ = run(lambda store: UnreachableModel())

    assert report.as_json()["unjudged"] == report.total
