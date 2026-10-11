"""Seam: policy_for(category) -> the applicable Policy Clauses; material_evidence(category) -> the checklist."""

from src.agents.policy import material_evidence, policy_for
from src.contracts import DisputeCategory, Remedy

NO_SHOW = DisputeCategory.NO_SHOW_CHARGE


def clauses_by_id():
    return {clause.clause_id: clause for clause in policy_for(NO_SHOW)}


def test_no_show_policy_is_a_set_of_clauses_with_stable_ids_one_version_and_the_right_category():
    clauses = policy_for(NO_SHOW)

    assert set(clauses_by_id()) == {"NS-1", "NS-2", "NS-3", "NS-4", "NS-5", "NS-6", "NS-7"}
    assert len(clauses_by_id()) == len(clauses)
    assert {clause.version for clause in clauses} == {"mock-1"}
    assert {clause.category for clause in clauses} == {NO_SHOW}
    assert all(clause.text for clause in clauses)


def test_a_category_with_no_policy_yet_returns_no_clauses():
    assert policy_for(DisputeCategory.PROPERTY_DAMAGE) == []


def test_the_free_wait_and_no_show_threshold_ambiguity_is_resolved_in_the_wording():
    clauses = clauses_by_id()

    assert "arrival" in clauses["NS-2"].text and "not from the scheduled" in clauses["NS-2"].text
    assert "no-show threshold" in clauses["NS-3"].text and "free wait" in clauses["NS-3"].text


def test_the_policy_lists_the_closed_remedies_and_rules_out_a_partial_outcome():
    clauses = clauses_by_id()

    assert all(remedy.value in clauses["NS-5"].text for remedy in Remedy)
    assert "partial" in clauses["NS-6"].text.lower() and "no partial" in clauses["NS-6"].text.lower()


def test_the_material_evidence_checklist_is_kept_with_the_policy():
    assert list(material_evidence(NO_SHOW)) == [
        "driver_at_pickup",
        "arrival_vs_scheduled",
        "wait_timers",
        "contact_attempts",
        "rider_position",
    ]
