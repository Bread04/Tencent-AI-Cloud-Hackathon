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


def test_the_console_has_no_on_page_controls_and_hands_the_switch_table_to_the_script():
    page = TestClient(create_demo_app()).get("/").text

    assert 'type="checkbox"' not in page and "demo-controls" not in page
    assert all(f"&quot;name&quot;: &quot;{s.name}&quot;" in page for s in DEMO_SWITCHES)
