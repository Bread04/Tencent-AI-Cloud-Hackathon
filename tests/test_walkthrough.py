"""Seam: the Demo Day walkthrough (ticket 17). The steps are a table, rehearsed here on the scripted stub in one
store like the live server, and `docs/demo-script.md` has to tell the presenter the same steps in the same order."""

import re
import time
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from src.api import create_app
from src.api.demo import ReplayModel
from src.api.demo_switches import DEMO_SWITCHES
from src.api.walkthrough import STEPS, Step, rehearse, render
from src.contracts import BalanceOfEvidence, DisputeCategory, ReviewTrigger, RulingOutcome
from src.intake import load_catalog
from src.store import CaseStore

SCRIPT = Path(__file__).resolve().parents[1] / "docs" / "demo-script.md"
LABELS = {s.name: s.label for s in DEMO_SWITCHES}


def core_only(steps=STEPS):
    """The steps run before any switch is ticked: the three Core Agents alone."""
    return list(steps[: next(i for i, step in enumerate(steps) if step.tick)])


def rehearsed(steps=STEPS):
    return rehearse(catalog=load_catalog(), model_for=ReplayModel, steps=steps)


def test_every_step_of_the_walkthrough_ends_the_way_the_script_says_it_will():
    results = rehearsed()

    assert [r.step for r in results] == list(STEPS)
    assert [(r.step.dispute_id, r.problems) for r in results if r.problems] == []


def test_the_walkthrough_opens_with_the_core_agents_alone_and_then_turns_on_every_supporting_agent_once():
    ticked = [name for step in STEPS for name in step.tick]

    assert STEPS[0].tick == ()
    assert ticked == [s.name for s in DEMO_SWITCHES]  # each switch once, in the order the console shows them


def test_with_the_core_agents_alone_one_case_is_ruled_for_the_claimant_and_one_for_the_respondent():
    core = [r for r in rehearsed() if not r.switches_on]

    sides = {r.case.ruling.balance_of_evidence for r in core if not r.step.held_for}
    assert {BalanceOfEvidence.CLAIMANT, BalanceOfEvidence.RESPONDENT} <= sides
    assert all(not getattr(r.case.switches, s.field) for r in core for s in DEMO_SWITCHES)


def test_the_core_agents_alone_resolve_both_required_categories():
    catalog = load_catalog()
    core = {catalog.dispute(step.dispute_id).category for step in core_only()}

    assert {DisputeCategory.NO_SHOW_CHARGE, DisputeCategory.ROUTE_DEVIATION} <= core


def test_a_switch_stays_on_once_ticked_so_the_presenter_never_has_to_untick_one():
    results = rehearsed()

    on_so_far = set()
    for result in results:
        on_so_far |= set(result.step.tick)
        assert set(result.switches_on) == on_so_far
        assert {s.name for s in DEMO_SWITCHES if getattr(result.case.switches, s.field)} == set(result.switches_sent)
        assert on_so_far - set(result.switches_sent) <= {s.name for s in DEMO_SWITCHES if s.photos_only}  # greyed out in the console for a Dispute with no photos


def test_each_step_that_turns_a_switch_on_names_something_that_switch_puts_in_the_log_or_the_evidence():
    assert all(step.shows or step.evidence_from for step in STEPS if step.tick)


def test_the_walkthrough_ends_the_same_way_when_driven_through_the_api_the_way_the_console_and_review_screen_do():
    store, catalog = CaseStore(), load_catalog()
    client = TestClient(create_app(store=store, model=ReplayModel(store), catalog=catalog))
    on = []
    for number, step in enumerate(STEPS, start=1):
        on += step.tick
        photos = catalog.dispute(step.dispute_id).photos
        query = "&".join(f"{s.name}=true" for s in DEMO_SWITCHES if s.name in on and (photos or not s.photos_only))  # the console's `switchQuery`
        case_id = client.post(f"/api/disputes/{step.dispute_id}/run?{query}").json()["case_id"]
        body = finished(client, case_id)
        ruling = body["case"]["ruling"]
        assert body["run_error"] is None and ruling["outcome"] == step.outcome.value, f"step {number}"
        assert ruling["amount"] == (str(step.amount) if step.amount is not None else None), f"step {number}"
        assert (body["case"]["status"] == "pending_review") is bool(step.held_for), f"step {number}"
        if step.priority is not None:  # the Safety Incident: the reviewer finds it first in the queue
            assert client.get("/api/review").json()["cases"][0]["case_id"] == case_id
        if step.override:
            decided = client.post(f"/api/review/{case_id}/decision", json={"reviewer": "Demo reviewer", "decision": "override", "reason": step.override})
            assert decided.status_code == 200 and decided.json()["case"]["status"] == "notified"
            assert "precedent_added" in [event["kind"] for event in decided.json()["log"]]
        if step.cites_override:
            assert any(precedent_id.startswith("PREC-HO-") for precedent_id in ruling["cited_precedent_ids"])


def finished(client, case_id):
    for _ in range(200):
        body = client.get(f"/api/cases/{case_id}").json()
        if body["case"]["outcomes"] or body["run_error"]:
            return body
        time.sleep(0.02)
    raise AssertionError(f"{case_id} did not finish")


def test_a_step_that_does_not_end_as_scripted_is_reported_with_what_happened_instead():
    wrong = Step("DISP-003", "said to be rejected", RulingOutcome.REJECT, rules_for=BalanceOfEvidence.RESPONDENT)

    (result,) = rehearsed([wrong])

    assert any("uphold" in problem for problem in result.problems)
    assert "FAIL" in render([result]) and "PASS" not in render([result])


def test_a_case_that_should_be_held_but_is_ruled_is_a_problem_and_so_is_the_reverse():
    should_hold = Step("DISP-003", "said to be held", RulingOutcome.UPHOLD, amount=Decimal("5.00"), held_for=(ReviewTrigger.LOW_CONFIDENCE,))
    should_rule = Step("DISP-004", "said to be ruled", RulingOutcome.REJECT)

    held, ruled = rehearsed([should_hold, should_rule])

    assert held.problems == ["It should be held for a person but it was ruled without one."]
    assert len(ruled.problems) == 1 and "it should be ruled without one" in ruled.problems[0]


def test_a_quoted_confidence_or_priority_that_is_no_longer_true_is_a_problem():
    stale = Step("DISP-003", "figures out of date", RulingOutcome.UPHOLD, amount=Decimal("5.00"), confidence=0.9, priority=7)

    (result,) = rehearsed([stale])

    assert result.problems == ["Confidence was 0.8, not 0.9.", "The priority was 0, not 7."]


def test_the_short_version_without_the_skippable_steps_still_ends_as_scripted_and_keeps_both_sides_and_the_learning_pair():
    short = [step for step in STEPS if not step.skippable]

    results = rehearsed(short)

    assert 0 < len(short) < len(STEPS)
    assert [(r.step.dispute_id, r.problems) for r in results if r.problems] == []
    assert {BalanceOfEvidence.CLAIMANT, BalanceOfEvidence.RESPONDENT} <= {step.rules_for for step in core_only(short)}
    assert short[-2].override and short[-1].cites_override


def test_the_rehearsal_prints_one_line_per_step_and_the_count_that_passed():
    text = render(rehearsed())

    assert f"{len(STEPS)} of {len(STEPS)} steps" in text
    assert text.count("PASS") == len(STEPS)


# --- the written script follows the table ---------------------------------------------------------------------


def sections():
    """The script's numbered steps: each `### N. ...` heading with the text under it."""
    parts = re.split(r"^### (\d+)\. ", SCRIPT.read_text(encoding="utf-8"), flags=re.MULTILINE)
    return [(int(parts[i]), parts[i + 1].split("\n## ")[0]) for i in range(1, len(parts), 2)]


def test_the_script_names_the_ryde_case_study_before_anything_else_is_said():
    text = SCRIPT.read_text(encoding="utf-8")
    spoken = [line for line in text.splitlines() if line.startswith("> ")]  # quote blocks are the presenter's words

    assert "Ryde case study" in spoken[0] and "Multi-Agent Autonomous Dispute Resolution" in spoken[0] and "Digital Native Track" in spoken[0]
    assert text.index(spoken[0]) < text.index("### 1. ")
    assert "## Opening" in text[: text.index(spoken[0])]


def test_the_script_has_one_numbered_step_per_walkthrough_step_running_the_same_dispute():
    found = sections()

    assert [number for number, _ in found] == list(range(1, len(STEPS) + 1))
    for (_, body), step in zip(found, STEPS):
        assert re.findall(r"DISP-\d{3}", body.splitlines()[0]) == [step.dispute_id]


def test_each_step_of_the_script_names_exactly_the_switches_that_step_turns_on():
    for (number, body), step in zip(sections(), STEPS):
        told = re.findall(r"[Tt]urns on \*\*(.+?)\*\*", body)
        assert told == [LABELS[name] for name in step.tick], f"step {number}"


def test_each_step_of_the_script_states_the_outcome_amount_and_figures_the_rehearsal_checks():
    for (number, body), step in zip(sections(), STEPS):
        assert f"`{step.outcome.value}`" in body, f"step {number}"
        if step.amount is not None:
            assert f"SGD {step.amount}" in body, f"step {number}"
        for trigger in step.held_for:
            assert f"`{trigger.value}`" in body, f"step {number}"
        for precedent_id in step.cites:
            assert precedent_id in body, f"step {number}"
        if step.confidence is not None:
            assert f"Confidence {step.confidence:.2f}" in body, f"step {number}"
        if step.priority is not None:
            assert f"Priority {step.priority}" in body, f"step {number}"
        if step.override:
            assert step.override in body, f"step {number}"


def test_the_script_marks_exactly_the_skippable_steps_as_ones_that_can_be_skipped():
    marked = ["(can be skipped)" in body.splitlines()[0] for _, body in sections()]

    assert marked == [step.skippable for step in STEPS]


def test_the_script_says_which_case_is_ruled_for_the_claimant_and_which_for_the_respondent():
    core = list(zip(core_only(), (body for _, body in sections())))

    for side, words in ((BalanceOfEvidence.CLAIMANT, "ruled for the Claimant"), (BalanceOfEvidence.RESPONDENT, "ruled for the Respondent")):
        assert any(step.rules_for is side and words in body for step, body in core), words


def test_the_script_says_what_is_left_out_of_the_demo_and_how_to_rehearse_it():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "## Not in the demo" in text and "Fraud" in text
    assert "scripts.rehearse" in text
