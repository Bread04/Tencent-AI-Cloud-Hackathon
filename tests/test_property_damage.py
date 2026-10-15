"""Seam: Property Damage resolved end to end (ticket 15, ADR 0005). The driver claims a cleaning fee; photo findings are signals, never the sole reason."""

import json
from decimal import Decimal

import pytest

from src.agents.judge.numbers import authenticity_problems, cleaning_fee
from src.agents.policy import ALLOWED_REMEDIES, policy_for
from src.api.demo import ReplayModel
from src.contracts import CaseStatus, DisputeCategory, EvidenceStatus, Party, Remedy, ReviewTrigger, RulingOutcome, RulingStatus, Switches
from src.intake import load_catalog
from src.llm.stub import load_replies
from src.orchestrator import run_dispute
from src.store import CaseStore
from src.tools.evidence import gather_evidence

PHOTOS = Switches(image_analysis=True, escalation=True)
NO_PHOTO_ANALYSIS = Switches(escalation=True)


def run(dispute_id, switches=PHOTOS, photos=None, scripts=None):
    catalog, store = load_catalog(), CaseStore()
    dispute = catalog.dispute(dispute_id)
    if photos is not None:
        dispute = dispute.model_copy(update={"photos": photos})
    case = run_dispute(dispute, store=store, model=ReplayModel(store, scripts=scripts), catalog=catalog, switches=switches)
    return store, case


# --- Filing and policy ---------------------------------------------------------------------------------------------------------------------


def test_a_driver_files_a_property_damage_dispute_with_photos_and_is_the_claimant():
    dispute = load_catalog().dispute("DISP-011")

    assert dispute.category is DisputeCategory.PROPERTY_DAMAGE and dispute.claimant is Party.DRIVER
    assert dispute.photos == ["data/photos/seat-stain.png"]


def test_the_vehicle_condition_clauses_are_served_and_the_remedies_are_a_compensation_or_nothing():
    assert [c.clause_id for c in policy_for(DisputeCategory.PROPERTY_DAMAGE)] == ["R-07", "D-07"]
    assert ALLOWED_REMEDIES[DisputeCategory.PROPERTY_DAMAGE] == {
        RulingOutcome.UPHOLD: Remedy.COMPENSATION_TO_DRIVER,
        RulingOutcome.PARTIALLY_UPHOLD: Remedy.COMPENSATION_TO_DRIVER,
        RulingOutcome.REJECT: Remedy.NO_ACTION,
    }


def test_the_claim_the_trip_and_the_chat_become_evidence_items():
    catalog = load_catalog()

    items = {i.evidence_id: i for i in gather_evidence(catalog.dispute("DISP-011").trip_id, catalog)}

    assert {"EV-DAMAGE-1", "EV-TRIP-1", "EV-CHAT-1", "EV-HISTORY-1"} <= set(items)
    claim = items["EV-DAMAGE-1"]
    assert claim.source == "damage_claim" and claim.side.value == "driver" and claim.derived["claimed_fee"] == "40.00" and claim.derived["cap"] == "50.00"


# --- The cleaning-fee rule (ADR 0005) ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "claimed, outcome, expected",
    [
        ("40.00", RulingOutcome.UPHOLD, "40.00"),
        ("80.00", RulingOutcome.UPHOLD, "50.00"),  # capped
        ("40.00", RulingOutcome.PARTIALLY_UPHOLD, "20.00"),
        ("45.25", RulingOutcome.PARTIALLY_UPHOLD, "22.63"),  # half, cents rounded half-up
        ("40.00", RulingOutcome.REJECT, None),
    ],
)
def test_the_cleaning_fee_is_the_claimed_fee_up_to_the_cap_halved_for_a_partial_ruling(claimed, outcome, expected):
    assert cleaning_fee(Decimal(claimed), outcome) == (Decimal(expected) if expected else None)


# --- End to end ----------------------------------------------------------------------------------------------------------------------------------


def test_genuine_damage_is_upheld_and_the_amount_is_the_code_computed_fee():
    store, case = run("DISP-011")

    ruling = case.ruling
    assert ruling.outcome is RulingOutcome.UPHOLD and ruling.remedy is Remedy.COMPENSATION_TO_DRIVER
    assert ruling.amount == Decimal("40.00") and ruling.calculation.input_evidence_ids == ["EV-DAMAGE-1"] and "ADR 0005" in ruling.calculation.formula
    assert ruling.status is RulingStatus.FINAL and case.status is CaseStatus.NOTIFIED
    assert {"EV-PHOTO-1-TIME", "EV-PHOTO-1-AI"} <= set(ruling.cited_evidence_ids)


def test_each_party_is_told_in_terms_of_the_drivers_cleaning_fee_claim():
    _, case = run("DISP-011")

    texts = {o.party: o.ruling_summary for o in case.outcomes}
    assert "cleaning fee" in texts[Party.DRIVER] and "SGD 40.00" in texts[Party.DRIVER] and "Your claim was upheld" in texts[Party.DRIVER]
    assert "driver's claim" in texts[Party.RIDER]


def test_a_photo_from_another_date_caps_confidence_and_sends_the_case_to_a_person():
    _, case = run("DISP-012")

    assert case.status is CaseStatus.PENDING_REVIEW
    assert case.ruling.status is RulingStatus.PROPOSAL and case.ruling.confidence.value <= 0.5
    assert case.ruling.confidence.components["authenticity"] == 0.5
    assert ReviewTrigger.AUTHENTICITY_CHECK in {t.trigger for t in case.ruling.review_triggers}


def test_a_photo_that_looks_ai_generated_caps_confidence_and_a_partial_ruling_still_gets_half_the_fee():
    _, case = run("DISP-013")

    assert case.ruling.outcome is RulingOutcome.PARTIALLY_UPHOLD and case.ruling.amount == Decimal("20.00")
    assert case.status is CaseStatus.PENDING_REVIEW and case.ruling.confidence.value <= 0.5
    assert ReviewTrigger.AUTHENTICITY_CHECK in {t.trigger for t in case.ruling.review_triggers}


def test_an_unanalysed_photo_counts_as_an_unknown_check():
    case = run("DISP-011")[1]
    unknown = case.model_copy(update={"evidence": [
        i.model_copy(update={"status": EvidenceStatus.MISSING}) if i.evidence_id == "EV-PHOTO-1-AI" else i for i in case.evidence
    ]})

    assert any("EV-PHOTO-1-AI" in problem for problem in authenticity_problems(unknown))


def test_with_photo_analysis_off_the_photo_is_stored_and_the_case_still_gets_a_ruling_with_lower_confidence():
    _, with_analysis = run("DISP-011")
    _, without = run("DISP-011", switches=NO_PHOTO_ANALYSIS)

    assert without.ruling is not None and without.dispute.photos
    assert without.ruling.confidence.value <= with_analysis.ruling.confidence.value
    assert not [i for i in without.evidence if i.source == "photo_finding"]


def test_a_case_with_no_photos_at_all_still_gets_a_ruling_with_lower_confidence():
    _, with_photo = run("DISP-011")
    _, no_photo = run("DISP-011", switches=NO_PHOTO_ANALYSIS, photos=[])  # nothing to analyse, so no photo overlay

    assert no_photo.ruling is not None and no_photo.ruling.confidence.value < 1
    assert no_photo.ruling.confidence.value <= with_photo.ruling.confidence.value
    assert no_photo.ruling.confidence.components["evidence_completeness"] < with_photo.ruling.confidence.components["evidence_completeness"]


def test_a_ruling_that_rests_only_on_a_failed_authenticity_check_is_sent_back_and_then_held():
    replies = load_replies("DISP-012", "photos")
    only_photo = {**replies["judge"], "cited_evidence_ids": ["EV-PHOTO-1-TIME"]}
    store, case = run("DISP-012", scripts={"DISP-012": {**replies, "judge": only_photo}})

    assert case.ruling is None and case.status is CaseStatus.PENDING_REVIEW
    held = next(e for e in store.log(case.case_id) if e.kind.value == "escalated")
    assert "sole reason" in held.summary


def test_the_earlier_categories_still_resolve_with_the_photo_switch_on():
    _, case = run("DISP-003")

    assert case.ruling.outcome is RulingOutcome.UPHOLD and case.status is CaseStatus.NOTIFIED


# --- A person reviews a held photo case ----------------------------------------------------------------------------------------------------


def test_a_reviewer_can_confirm_or_override_a_held_property_damage_case_and_the_fee_is_recomputed_by_code():
    from src.agents.escalation import ReviewDecision, decide_review

    store, case = run("DISP-012")
    confirmed = decide_review(store, case.case_id, reviewer="A. Reviewer", decision=ReviewDecision.CONFIRM)
    assert confirmed.ruling.outcome is RulingOutcome.REJECT and confirmed.ruling.amount is None and confirmed.status is CaseStatus.NOTIFIED

    store, case = run("DISP-012")
    overridden = decide_review(store, case.case_id, reviewer="A. Reviewer", decision=ReviewDecision.OVERRIDE, reason="The driver's earlier job record shows a clean seat.")
    assert overridden.ruling.outcome is RulingOutcome.UPHOLD and overridden.ruling.amount == Decimal("40.00")


# --- The console ------------------------------------------------------------------------------------------------------------------------------


def test_the_console_serves_the_photos_and_marks_the_disputes_that_have_them():
    from fastapi.testclient import TestClient

    from src.api.demo import create_demo_app

    client = TestClient(create_demo_app())
    page = client.get("/").text

    assert client.get("/photos/seat-stain.png").headers["content-type"] == "image/png"
    assert "data-dispute='DISP-011'" in page and page.count("data-photos=1") == 3 and "&quot;needsPhotos&quot;: true" in page


def test_a_held_cleaning_fee_case_tells_both_parties_the_proposed_outcome_and_that_a_person_will_confirm_it():
    _, case = run("DISP-013")

    assert case.status is CaseStatus.PENDING_REVIEW
    for outcome in case.outcomes:
        assert outcome.action_status.value == "pending_review"
        assert "proposed" in outcome.ruling_summary.lower() and "SGD 20.00" in outcome.ruling_summary
        assert "person" in outcome.ruling_summary.lower() and "confirm" in outcome.ruling_summary.lower()
