"""The shared contract: every object accepts good input and rejects bad input clearly."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from tests import builders as b

BUILDERS = [
    b.a_dispute,
    b.an_evidence_item,
    b.a_submission,
    b.a_policy_clause,
    b.a_precedent,
    b.a_ruling,
    b.an_outcome,
    b.a_log_event,
    b.a_case,
]


def rejected(build, **bad_fields) -> str:
    """Build with bad input and return the error text a developer or model would see."""
    with pytest.raises(ValidationError) as error:
        build(**bad_fields)
    return str(error.value)


@pytest.mark.parametrize("build", BUILDERS)
def test_good_input_validates_and_survives_a_json_round_trip(build):
    obj = build()

    assert type(obj).model_validate_json(obj.model_dump_json()) == obj


@pytest.mark.parametrize("build", BUILDERS)
def test_unknown_fields_are_rejected_by_name(build):
    assert "not_in_the_contract" in rejected(build, not_in_the_contract=1)


# --- Dispute ---------------------------------------------------------------


def test_dispute_names_claimant_and_respondent_from_who_filed():
    assert b.a_dispute(filed_by="rider").claimant == "rider"
    assert b.a_dispute(filed_by="rider").respondent == "driver"
    assert b.a_dispute(filed_by="driver").respondent == "rider"


def test_dispute_rejects_an_unknown_category_naming_the_field_and_the_choices():
    error = rejected(b.a_dispute, category="lost_item")

    assert "category" in error
    assert "no_show_charge" in error


def test_dispute_rejects_an_empty_description():
    assert "description" in rejected(b.a_dispute, description="")


# --- Evidence Item ---------------------------------------------------------


def test_missing_evidence_is_a_valid_item_with_its_cause():
    item = b.an_evidence_item(status="missing", content="GPS provider returned no trace", timestamp=None, derived={})

    assert item.status == "missing"


def test_evidence_item_rejects_an_unknown_status():
    assert "status" in rejected(b.an_evidence_item, status="probably_fine")


def test_conflicting_evidence_must_link_the_items_it_conflicts_with():
    assert "conflicts_with" in rejected(b.an_evidence_item, status="conflicting")

    linked = b.an_evidence_item(status="conflicting", conflicts_with=["EV-CHAT-3"])
    assert linked.conflicts_with == ["EV-CHAT-3"]


# --- Submission ------------------------------------------------------------


def test_submission_rejects_an_author_that_is_not_an_advocate():
    assert "author" in rejected(b.a_submission, author="judge")


def test_submission_rejects_a_counter_argument_without_a_response():
    error = rejected(b.a_submission, counter_arguments=[{"argument": "The driver waited."}])

    assert "response" in error


# --- Policy Clause and Precedent -------------------------------------------


def test_policy_clause_requires_a_version():
    assert "version" in rejected(b.a_policy_clause, version=None)


def test_precedent_from_a_human_override_must_carry_the_override_reason():
    assert "override_reason" in rejected(b.a_precedent, source="human_override")

    overridden = b.a_precedent(source="human_override", override_reason="Timer started before arrival.")
    assert overridden.source == "human_override"


# --- Ruling ----------------------------------------------------------------


def test_ruling_rejects_an_outcome_outside_uphold_partially_uphold_reject():
    assert "outcome" in rejected(b.a_ruling, outcome="split_the_difference")


def test_ruling_rejects_a_remedy_outside_the_closed_list():
    assert "remedy" in rejected(b.a_ruling, remedy="free_rides_for_a_year")


def test_ruling_amount_must_equal_the_calculation_it_shows():
    error = rejected(b.a_ruling, amount="7.50")

    assert "amount" in error and "calculation" in error


def test_ruling_amount_needs_a_currency_and_a_calculation():
    assert "currency" in rejected(b.a_ruling, currency=None)
    assert "calculation" in rejected(b.a_ruling, calculation=None)


def test_ruling_without_an_amount_is_valid():
    ruling = b.a_ruling(outcome="reject", remedy="no_action", amount=None, currency=None, calculation=None)

    assert ruling.amount is None


def test_ruling_amount_is_exact_money_not_a_float():
    assert b.a_ruling().amount == Decimal("5.00")


def test_ruling_rejects_an_argument_assessment_with_an_unknown_verdict():
    assessment = b.a_ruling().argument_assessments[0].model_dump() | {"verdict": "mostly_true"}

    assert "verdict" in rejected(b.a_ruling, argument_assessments=[assessment])


def test_ruling_confidence_must_be_between_0_and_1():
    assert "confidence" in rejected(b.a_ruling, confidence={"value": 1.2, "components": {}})
    assert "confidence" in rejected(b.a_ruling, confidence={"value": 0.9, "components": {"policy_fit": -0.1}})


def test_a_final_ruling_must_carry_its_calculated_confidence():
    assert "confidence" in rejected(b.a_ruling, status="final", confidence=None)

    draft = b.a_ruling(status="proposal", confidence=None)
    assert draft.confidence is None


def test_a_policy_gap_makes_policy_fit_unclear():
    assert "policy_fit" in rejected(b.a_ruling, policy_gap="No clause covers a blocked pickup road.")

    ruling = b.a_ruling(policy_gap="No clause covers a blocked pickup road.", policy_fit="unclear")
    assert ruling.policy_fit == "unclear"


def test_ruling_rejects_an_unknown_review_trigger():
    trigger = {"trigger": "gut_feeling", "reason": "Something seems off."}

    assert "trigger" in rejected(b.a_ruling, review_triggers=[trigger])


# --- Outcome and Log event -------------------------------------------------


def test_outcome_rejects_an_unknown_action_status():
    assert "action_status" in rejected(b.an_outcome, action_status="paid")


def test_log_event_rejects_a_kind_that_is_not_in_the_communication_log():
    assert "kind" in rejected(b.a_log_event, kind="model_thoughts")


# --- Case ------------------------------------------------------------------


def test_a_new_case_is_filed_with_every_supporting_agent_switched_off():
    case = b.a_case()

    assert case.status == "filed"
    assert not any(case.switches.model_dump().values())


def test_case_rejects_a_status_outside_the_lifecycle():
    assert "status" in rejected(b.a_case, status="on_hold")


def test_case_rejects_two_submissions_from_the_same_advocate():
    twice = [b.a_submission(author="rider_advocate"), b.a_submission(author="rider_advocate")]

    assert "rider_advocate" in rejected(b.a_case, submissions=twice)
