"""Configuration: the Supporting Agent switches and the contract-session decisions the code reads.

Expected values are the proposals in docs/architecture.md (sections 5.7, 6.1, 6.2, 6.4).
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.config import CONFIG, Config
from src.contracts import Switches


def test_every_supporting_agent_has_a_switch_and_only_escalation_is_on_by_default():
    assert CONFIG.switches.model_dump() == {
        "evidence_agents": False,
        "policy_precedent": False,
        "image_analysis": False,
        "escalation": True,
        "sla_routing": False,
        "learning_loop": False,
    }


def test_a_switch_can_be_turned_on_without_touching_the_defaults():
    demo = CONFIG.model_copy(update={"switches": Switches(learning_loop=True)})

    assert demo.switches.learning_loop is True
    assert CONFIG.switches.learning_loop is False


def test_a_misspelt_switch_is_rejected():
    with pytest.raises(ValidationError) as error:
        Switches(escalaton=True)

    assert "escalaton" in str(error.value)


def test_confidence_components_use_the_proposed_starting_values():
    confidence = CONFIG.confidence

    assert confidence.policy_fit == {"clear": 0.95, "arguable": 0.75, "unclear": 0.5}
    assert (confidence.consistency_no_conflict, confidence.consistency_conflict) == (0.95, 0.65)
    assert (confidence.stability_agree, confidence.stability_disagree) == (0.95, 0.5)
    assert confidence.authenticity_failed_or_unknown == 0.5
    assert confidence.decisive_own_finding_cap == 0.75
    assert (confidence.history_step, confidence.history_max) == (0.05, 0.2)


def test_escalation_threshold_defaults_to_0_7_and_is_configurable():
    assert CONFIG.escalation.confidence_threshold == 0.7

    stricter = Config(escalation={"confidence_threshold": 0.8})
    assert stricter.escalation.confidence_threshold == 0.8


def test_escalation_triggers_are_the_nine_proposed_ones():
    assert set(CONFIG.escalation.triggers) == {
        "low_confidence",
        "balanced_evidence",
        "policy_gap",
        "safety_incident",
        "authenticity_check",
        "stability_disagreement",
        "history_rule",
        "stage_failed",
        "amount_over_limit",
    }


def test_the_ruling_amount_limit_is_exact_money_in_a_stated_currency():
    assert isinstance(CONFIG.escalation.amount_limit, Decimal)
    assert CONFIG.currency == "SGD"


def test_structured_output_is_schema_constrained_json_with_two_repair_attempts():
    assert CONFIG.model.structured_output == "json_schema"
    assert CONFIG.model.repair_attempts == 2


def test_no_show_charge_has_its_five_item_material_evidence_checklist():
    checklist = CONFIG.material_evidence["no_show_charge"]

    assert list(checklist) == [
        "driver_at_pickup",
        "arrival_vs_scheduled",
        "wait_timers",
        "contact_attempts",
        "rider_position",
    ]


def test_history_rules_can_only_lower_confidence_or_ask_for_review():
    assert CONFIG.history_rules, "the History rule table must not be empty"
    for rule in CONFIG.history_rules:
        assert rule.lowers_confidence or rule.triggers_review


def test_a_confidence_value_outside_0_to_1_is_rejected():
    with pytest.raises(ValidationError) as error:
        Config(escalation={"confidence_threshold": 1.5})

    assert "confidence_threshold" in str(error.value)
