"""Seam: the Judge's stability check (architecture 6.7): two passes with the Submission order swapped, compared by code."""

import json

import pytest

from src.agents.judge import judge
from src.agents.judge.stability import StabilityResult, compare, submission_order_flipped
from src.config import CONFIG
from src.contracts import CaseStatus, LogEventKind, ReviewTrigger, RulingOutcome, RulingStatus, Switches
from src.intake import load_catalog
from src.llm import ModelError, StubModel
from src.orchestrator import run_dispute
from src.store import CaseStore

from tests.cases import a_stub_for, fixture_submissions
from tests.test_judge import SELF_CHECK_PASSES, a_judge_draft, an_assessment

MARGIN = CONFIG.confidence.stability_margin
ON = Switches(stability_check=True, escalation=True)

# The same Judge draft with the verdict turned round: a Judge swayed by the order would do this.
UPHOLD = dict(outcome="uphold", remedy="fee_reversal", balance_of_evidence="claimant", amount_input_evidence_ids=["EV-FARE-1"])


def a_case(switches=ON):
    from src.tools.evidence import gather_evidence

    catalog, store = load_catalog(), CaseStore()
    dispute = catalog.dispute("DISP-002")
    case = store.create_case(dispute, switches)
    store.add_evidence(case.case_id, gather_evidence(dispute.trip_id, catalog), agent="evidence")
    store.seal_evidence(case.case_id)
    return store.get_case(case.case_id)


def run(first, second=None, switches=ON, second_error=None):
    case = a_case(switches)
    rider, driver = fixture_submissions()
    script = {(case.case_id, "judge"): first, (case.case_id, "judge_self_check"): SELF_CHECK_PASSES}
    if second is not None:
        script[(case.case_id, "judge_second_pass")] = second
    model = StubModel(script)
    events = []
    ruling = judge(case, rider, driver, model, record=lambda kind, summary, references=None: events.append((kind, summary)))
    return ruling, model, events


def prompt(model, agent):
    return json.dumps(next(c["messages"] for c in model.calls if c["agent"] == agent))


# --- The comparison: pure code -------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "first, second, agrees",
    [
        ((RulingOutcome.REJECT, 0.8), (RulingOutcome.REJECT, 0.8), True),
        ((RulingOutcome.REJECT, 0.8), (RulingOutcome.REJECT, 0.8 - MARGIN), True),  # a gap exactly at the margin still agrees
        ((RulingOutcome.REJECT, 0.8), (RulingOutcome.REJECT, 0.65), False),  # a gap above the margin does not
        ((RulingOutcome.REJECT, 0.8), (RulingOutcome.UPHOLD, 0.8), False),  # a different outcome never does
    ],
)
def test_two_passes_agree_when_the_outcome_matches_and_confidence_is_within_the_margin(first, second, agrees):
    assert compare(first, second, margin=MARGIN).agrees is agrees


def test_the_order_is_set_by_the_case_so_it_varies_between_cases_but_never_for_one_case():
    flips = {submission_order_flipped(f"CASE-{n:04d}") for n in range(1, 21)}

    assert flips == {True, False}
    assert submission_order_flipped("CASE-0007") == submission_order_flipped("CASE-0007")


# --- Presentation ---------------------------------------------------------------------------------------------------------


def test_submissions_are_shown_under_neutral_labels_and_the_second_pass_reads_them_in_the_other_order():
    _, model, _ = run(a_judge_draft(), a_judge_draft())

    first, second = prompt(model, "judge"), prompt(model, "judge_second_pass")
    for text in (first, second):
        assert "Submission A" in text and "Submission B" in text
        assert "Rider Advocate Submission" not in text and "Driver Advocate Submission" not in text
    assert (first.index("RIDER-MARKER") < first.index("DRIVER-MARKER")) != (second.index("RIDER-MARKER") < second.index("DRIVER-MARKER"))


def test_with_the_check_off_the_prompt_is_unchanged_and_there_is_one_pass():
    _, model, events = run(a_judge_draft(), switches=Switches(escalation=True))

    assert "Rider Advocate Submission" in prompt(model, "judge")
    assert [c for c in model.calls if c["agent"] == "judge_second_pass"] == []
    assert not [e for e in events if e[0] is LogEventKind.STABILITY_CHECK]


# --- Agreement and disagreement -------------------------------------------------------------------------------------------------


def test_two_agreeing_passes_are_recorded_and_the_ruling_is_unchanged():
    ruling, model, events = run(a_judge_draft(), a_judge_draft())

    assert len([c for c in model.calls if c["agent"] == "judge_second_pass"]) == 1
    assert ruling.status is RulingStatus.FINAL and not ruling.review_triggers
    assert ruling.confidence.components["stability"] == CONFIG.confidence.stability_agree
    (_, summary) = next(e for e in events if e[0] is LogEventKind.STABILITY_CHECK)
    assert "agree" in summary


def test_a_different_outcome_on_the_second_pass_escalates_with_stability_disagreement_and_caps_confidence():
    ruling, _, events = run(a_judge_draft(), a_judge_draft(**UPHOLD))

    assert ruling.status is RulingStatus.PROPOSAL
    assert ReviewTrigger.STABILITY_DISAGREEMENT in [t.trigger for t in ruling.review_triggers]
    assert ruling.confidence.value <= CONFIG.confidence.stability_disagree
    (_, summary) = next(e for e in events if e[0] is LogEventKind.STABILITY_CHECK)
    assert "disagree" in summary and "reject" in summary and "uphold" in summary


def test_a_confidence_gap_above_the_margin_also_escalates():
    shaky = a_judge_draft(policy_fit="unclear", policy_fit_reason="Unclear.", policy_gap="No clause covers it.")  # 0.5 against 0.8

    ruling, _, _ = run(a_judge_draft(), shaky)

    assert ReviewTrigger.STABILITY_DISAGREEMENT in [t.trigger for t in ruling.review_triggers]


def test_a_small_confidence_gap_within_the_margin_does_not():
    slightly_less_sure = a_judge_draft(policy_fit="arguable", policy_fit_reason="Arguable.")  # 0.75 against 0.8: gap 0.05

    ruling, _, _ = run(a_judge_draft(), slightly_less_sure)

    assert ReviewTrigger.STABILITY_DISAGREEMENT not in [t.trigger for t in ruling.review_triggers]


def test_a_second_pass_that_cannot_be_completed_escalates_rather_than_passing_unchecked():
    case = a_case()
    rider, driver = fixture_submissions()
    model = StubModel({(case.case_id, "judge"): a_judge_draft(), (case.case_id, "judge_self_check"): SELF_CHECK_PASSES})  # nothing for the second pass

    ruling = judge(case, rider, driver, model)

    assert ruling.status is RulingStatus.PROPOSAL
    assert "could not be completed" in next(t for t in ruling.review_triggers if t.trigger is ReviewTrigger.STABILITY_DISAGREEMENT).reason


# --- In a whole run -----------------------------------------------------------------------------------------------------------------


def test_a_disagreement_holds_the_case_for_review_and_the_log_says_why():
    catalog, store = load_catalog(), CaseStore()
    replies = {("CASE-0001", "judge"): a_judge_draft(), ("CASE-0001", "judge_second_pass"): a_judge_draft(**UPHOLD)}
    base = a_stub_for("CASE-0001", "DISP-002")
    model = StubModel({**{(c, a): r for (c, a), r in base._script.items()}, **replies})

    case = run_dispute(catalog.dispute("DISP-002"), store=store, model=model, catalog=catalog, switches=ON)

    assert case.status is CaseStatus.PENDING_REVIEW
    assert ReviewTrigger.STABILITY_DISAGREEMENT in [t.trigger for t in case.ruling.review_triggers]
    assert [e for e in store.log(case.case_id) if e.kind is LogEventKind.STABILITY_CHECK]
