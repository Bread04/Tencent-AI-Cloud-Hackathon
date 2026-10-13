"""Seam: the demo's switch table. One row per switch drives the API, the console checkboxes and the recorded streams."""

import itertools
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.demo import create_demo_app
from src.api.demo_switches import DEMO_SWITCHES, applicable_switches, switches_from_query
from src.config import CONFIG
from src.contracts import Case, Switches
from src.intake import load_catalog

RECORDED = Path(__file__).resolve().parents[1] / "src" / "api" / "static" / "recorded"


def test_every_row_names_a_real_switch_and_the_names_are_unique():
    assert {s.field for s in DEMO_SWITCHES} <= set(Switches.model_fields)
    assert len({s.name for s in DEMO_SWITCHES}) == len(DEMO_SWITCHES)


def test_no_switches_in_the_query_means_the_configured_defaults():
    assert switches_from_query({}) is None


def test_a_switch_in_the_query_turns_that_one_on_and_leaves_the_rest_as_configured():
    chosen = switches_from_query({"stability": "true"})

    assert chosen.stability_check is True
    assert chosen.policy_precedent == CONFIG.switches.policy_precedent and chosen.escalation == CONFIG.switches.escalation


@pytest.mark.parametrize("value", ["false", "0", "no", ""])
def test_a_switch_that_is_not_true_is_not_turned_on(value):
    assert switches_from_query({"routing": value}) is None


def test_the_console_has_one_checkbox_per_switch_in_the_table_order():
    page = TestClient(create_demo_app()).get("/").text

    positions = [page.index(f'data-switch="{s.name}"') for s in DEMO_SWITCHES]
    assert positions == sorted(positions)
    assert all(s.label in page for s in DEMO_SWITCHES)


def combinations(dispute_id):
    applicable = applicable_switches(load_catalog().dispute(dispute_id))  # photo analysis only counts for a Dispute with photos
    return [tuple(s.name for s, on in zip(applicable, flags) if on) for flags in itertools.product([False, True], repeat=len(applicable))]


@pytest.mark.parametrize("dispute_id", sorted(load_catalog().disputes))
def test_every_dispute_has_a_recorded_stream_for_every_combination_of_the_switches_that_can_change_it(dispute_id):
    for names in combinations(dispute_id):
        path = RECORDED / (".".join([dispute_id, *names]) + ".json")
        case = Case.model_validate(json.loads(path.read_text(encoding="utf-8"))["case"])
        for switch in DEMO_SWITCHES:  # each is off by default, so a stream has it on exactly when its name is in the file name
            assert getattr(case.switches, switch.field) is (switch.name in names), path.name


def test_photo_analysis_is_offered_only_for_a_dispute_with_photos():
    catalog = load_catalog()

    assert "photos" in [s.name for s in applicable_switches(catalog.dispute("DISP-011"))]
    assert "photos" not in [s.name for s in applicable_switches(catalog.dispute("DISP-003"))]


@pytest.mark.parametrize("dispute_id", sorted(load_catalog().disputes))
def test_no_recorded_stream_holds_a_run_that_failed_for_want_of_a_scripted_reply(dispute_id):
    for names in combinations(dispute_id):
        path = RECORDED / (".".join([dispute_id, *names]) + ".json")
        assert "no scripted reply" not in path.read_text(encoding="utf-8"), path.name
