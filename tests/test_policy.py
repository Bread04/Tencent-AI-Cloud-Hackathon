"""Seam: policy_for(category) -> the applicable Policy Clauses; material_evidence(category) -> the checklist.

The policy source is the shared Waypoint set (prototypes/shared/policies.js, ported to data/policy/).
It is deliberately generic: it sets no wait time or fee. Thresholds come from the trip's fare evidence.
"""

import json
import re
import shutil
import subprocess

import pytest

from src.agents.policy import POLICY_DIR, SIMULATED_LABEL, material_evidence, policy_for
from src.contracts import DisputeCategory

NO_SHOW = DisputeCategory.NO_SHOW_CHARGE
SOURCE = POLICY_DIR.parents[1] / "prototypes" / "shared" / "policies.js"


def clauses_by_id():
    return {clause.clause_id: clause for clause in policy_for(NO_SHOW)}


def test_no_show_policy_is_the_shared_waypoint_clauses_for_pickup_fare_and_reporting():
    clauses = policy_for(NO_SHOW)

    assert set(clauses_by_id()) == {"R-01", "R-02", "R-03", "R-06", "D-02", "D-03", "D-06", "D-09"}
    assert len(clauses_by_id()) == len(clauses)
    assert {clause.version for clause in clauses} == {"waypoint-singapore-draft-2026-10"}
    assert {clause.category for clause in clauses} == {NO_SHOW}  # the category they are served for
    assert all(clause.text for clause in clauses)


def test_a_category_with_no_policy_mapped_yet_returns_no_clauses():
    assert policy_for(DisputeCategory.PROPERTY_DAMAGE) == []


def test_the_policy_invents_no_wait_time_or_fee():
    for clause in policy_for(NO_SHOW):
        assert not re.search(r"\d+\s*(minute|min)\b|\$\s*\d|SGD\s*\d", clause.text, re.I), clause.clause_id


def test_the_policy_is_labelled_as_draft_and_not_ryde_approved():
    assert "draft" in SIMULATED_LABEL.lower() and "not ryde" in SIMULATED_LABEL.lower()


def test_the_material_evidence_checklist_is_kept_with_the_policy():
    assert list(material_evidence(NO_SHOW)) == [
        "driver_at_pickup",
        "arrival_vs_scheduled",
        "wait_timers",
        "contact_attempts",
        "rider_position",
    ]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is needed to read the JS policy source")
def test_the_ported_policy_text_is_identical_to_the_prototype_source():
    script = f"const p=require({json.dumps(str(SOURCE))});console.log(JSON.stringify({{v:p.version,c:p.clauses.map(c=>[c.id,c.text])}}))"
    source = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True).stdout)

    ported = json.loads((POLICY_DIR / f"{source['v']}.json").read_text(encoding="utf-8"))
    assert [[c["clause_id"], c["text"]] for c in ported["clauses"]] == source["c"]


def test_safety_incidents_are_served_the_safety_clauses_in_full_to_every_agent():
    assert [clause.clause_id for clause in policy_for(DisputeCategory.SAFETY_INCIDENT)] == ["R-05", "R-06", "D-05", "D-06"]
