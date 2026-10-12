"""Seam: the SLA & Routing Manager (architecture 5.1): a Priority and a reason for every Case, and intake classification."""

from decimal import Decimal

import pytest

from src.agents.intake import IntakeError, classify, resolve_category
from src.agents.routing import score
from src.contracts import DisputeCategory

from tests.builders import a_dispute


def priority(category, description="A plain complaint.", fee="5.00"):
    return score(a_dispute(category=category, description=description), Decimal(fee))


# --- Priority from category, urgency and value -------------------------------------------------------------------------------


def test_a_safety_incident_outranks_every_other_category():
    safety = priority("safety_incident").value

    assert all(safety > priority(other).value for other in ("no_show_charge", "route_deviation", "property_damage"))


def test_a_larger_fee_raises_priority_a_little_and_a_safety_word_in_any_category_raises_it_a_lot():
    plain = priority("no_show_charge", fee="5.00").value

    assert priority("no_show_charge", fee="95.00").value > plain
    assert priority("no_show_charge", "The driver drove dangerously and I felt unsafe.").value > plain + 20


def test_a_safety_word_in_an_ordinary_dispute_does_not_make_it_a_safety_incident_but_is_in_the_reason():
    result = priority("no_show_charge", "The driver was rude and I felt threatened.")

    assert "threat" in result.reason
    assert result.value < priority("safety_incident").value


def test_every_priority_comes_with_a_reason_that_names_the_category():
    for category in DisputeCategory:
        result = priority(category.value)
        assert result.reason and category.value.replace("_", " ") in result.reason.lower()


def test_the_same_dispute_always_gets_the_same_priority():
    assert priority("property_damage", "A stain on the seat.") == priority("property_damage", "A stain on the seat.")


# --- Classifying a description when no category is chosen --------------------------------------------------------------------


@pytest.mark.parametrize(
    "description, category",
    [
        ("The driver cancelled and charged me a no-show fee though I was waiting.", "no_show_charge"),
        ("The driver took a much longer route than the app showed.", "route_deviation"),
        ("There is a stain and a scratch on the seat after the ride.", "property_damage"),
        ("The driver ran a red light and I felt unsafe the whole way.", "safety_incident"),
    ],
)
def test_a_description_is_classified_into_a_category(description, category):
    assert classify(description).category.value == category


def test_a_safety_word_wins_over_a_milder_category_so_a_safety_report_is_never_filed_as_a_fee_dispute():
    assert classify("I was charged a cancellation fee and the driver threatened me.").category is DisputeCategory.SAFETY_INCIDENT


def test_a_description_that_fits_no_category_is_rejected_with_a_clear_error():
    with pytest.raises(IntakeError, match="could not tell which kind of dispute"):
        resolve_category(None, "Something happened.")


def test_a_chosen_category_is_kept_and_never_reclassified():
    assert resolve_category("route_deviation", "The driver ran a red light.") is DisputeCategory.ROUTE_DEVIATION


def test_a_chosen_category_that_does_not_exist_is_a_clear_error():
    with pytest.raises(IntakeError, match="not a dispute category"):
        resolve_category("lost_parcel", "My parcel is lost.")


# --- The API ------------------------------------------------------------------------------------------------------------------


def test_the_api_classifies_a_description_and_rejects_one_that_fits_no_category():
    from fastapi.testclient import TestClient

    from src.api.demo import create_demo_app

    client = TestClient(create_demo_app())

    ok = client.post("/api/classify", json={"description": "The driver ran a red light and I felt unsafe."})
    bad = client.post("/api/classify", json={"description": "Something happened."})

    assert ok.json() == {"category": "safety_incident", "chosen": False}
    assert bad.status_code == 422 and "could not tell which kind of dispute" in bad.json()["error"]
