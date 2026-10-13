"""Seam: the precedent store and retrieval (architecture 5.3, ADR 0003). Tags rank; an embedding model may rerank; a failed model falls back."""

import json
import re

import pytest

from src.agents.policy.precedents import (
    case_tags,
    eligible,
    retrieve_precedents,
    seeded_precedents,
)
from src.contracts import DisputeCategory, EvidenceItem, PrecedentSource
from src.intake import load_catalog
from src.store import CaseStore
from src.tools.evidence import gather_evidence


def a_sealed_case(dispute_id: str):
    catalog, store = load_catalog(), CaseStore()
    dispute = catalog.dispute(dispute_id)
    case = store.create_case(dispute)
    store.add_evidence(case.case_id, gather_evidence(dispute.trip_id, catalog), agent="evidence")
    store.seal_evidence(case.case_id)
    return store.get_case(case.case_id)


# --- The store ---------------------------------------------------------------------------------------------------------


def test_the_store_is_seeded_for_every_category_and_every_precedent_says_its_source():
    seeded = seeded_precedents()

    assert {p.category for p in seeded} == {DisputeCategory.NO_SHOW_CHARGE, DisputeCategory.ROUTE_DEVIATION, DisputeCategory.SAFETY_INCIDENT}
    assert len({p.precedent_id for p in seeded}) == len(seeded)
    assert {p.source for p in seeded} == {PrecedentSource.SEEDED}


def test_only_seeded_and_human_reviewed_precedents_are_retrievable_never_an_unreviewed_model_ruling():
    seeded = seeded_precedents()
    base = seeded[0]
    model = base.model_copy(update={"precedent_id": "PREC-MODEL", "source": PrecedentSource.MODEL})
    confirmed = base.model_copy(update={"precedent_id": "PREC-CONF", "source": PrecedentSource.HUMAN_CONFIRMED})
    override = base.model_copy(update={"precedent_id": "PREC-OVER", "source": PrecedentSource.HUMAN_OVERRIDE, "override_reason": "A reviewer disagreed."})

    kept = {p.precedent_id for p in eligible([model, confirmed, override, *seeded])}

    assert "PREC-MODEL" not in kept
    assert {"PREC-CONF", "PREC-OVER"} <= kept


PARTY_ID = re.compile(r"\b[RD]-\d{4}\b")  # R-7824, D-2399: a rider or driver ID, not a policy clause like R-02
FORBIDDEN = [PARTY_ID, re.compile(r"TRIP-"), re.compile(r"DISP-"), re.compile(r"CASE-\d"), re.compile(r"EV-HISTORY"), re.compile(r"fraud", re.I),
             re.compile(r"prior (rejected )?disputes?", re.I), re.compile(r"dispute history", re.I), re.compile(r"flagged", re.I)]


def test_no_precedent_holds_a_party_identifier_a_trip_id_or_anything_derived_from_history():
    for precedent in seeded_precedents():
        text = precedent.model_dump_json()
        for pattern in FORBIDDEN:
            assert not pattern.search(text), f"{precedent.precedent_id} matches {pattern.pattern}"


# --- Tags from the Case --------------------------------------------------------------------------------------------------


def test_the_tags_describe_the_case_from_the_sealed_evidence_and_never_from_history():
    assert case_tags(a_sealed_case("DISP-003")) == {
        "driver_at_pickup", "driver_on_time", "free_wait_not_over", "no_show_threshold_not_reached", "driver_contacted_rider",
        "rider_replied", "rider_location_missing",
    }
    assert case_tags(a_sealed_case("DISP-002")) == {
        "driver_at_pickup", "driver_on_time", "free_wait_over", "no_show_threshold_reached", "driver_contacted_rider", "rider_location_missing",
    }


# --- Retrieval ---------------------------------------------------------------------------------------------------------------


def test_the_most_similar_precedent_comes_first_with_the_reason_it_is_similar():
    result = retrieve_precedents(a_sealed_case("DISP-003"), seeded_precedents())

    first = result.served[0]
    assert first.precedent.ruling.outcome.value == "uphold"  # the four-minute wait precedent
    assert "free_wait_not_over" in first.shared_tags
    assert "free wait not over" in first.why and first.precedent.source is PrecedentSource.SEEDED


def test_only_the_cases_own_category_is_served_and_at_most_a_few():
    result = retrieve_precedents(a_sealed_case("DISP-002"), seeded_precedents())

    assert 0 < len(result.served) <= 3
    assert {s.precedent.category for s in result.served} == {DisputeCategory.NO_SHOW_CHARGE}


def test_ties_break_by_id_so_the_same_case_always_gets_the_same_precedents():
    case = a_sealed_case("DISP-004")

    assert [s.precedent.precedent_id for s in retrieve_precedents(case, seeded_precedents()).served] == [
        s.precedent.precedent_id for s in retrieve_precedents(case, list(reversed(seeded_precedents()))).served
    ]


def test_a_precedent_sharing_no_tags_is_not_served():
    case = a_sealed_case("DISP-003")
    odd = seeded_precedents()[0].model_copy(update={"precedent_id": "PREC-ODD", "similarity_tags": ["unrelated_tag"]})

    assert retrieve_precedents(case, [odd]).served == []


def test_with_nothing_found_the_result_says_so():
    result = retrieve_precedents(a_sealed_case("DISP-003"), [])

    assert result.served == [] and "No precedent found" in result.note


# --- Embeddings: a rerank, with a fallback ----------------------------------------------------------------------------------------


class FakeEmbedder:
    """Puts the text that mentions 'unanswered' closest to the query, whatever the tags say."""

    def embed(self, texts):
        return [[1.0, 0.0] if "unanswered" in t else [0.0, 1.0] for t in texts]


def test_embeddings_rerank_the_tag_candidates_when_a_model_is_available():
    case = a_sealed_case("DISP-002")
    pool = seeded_precedents()
    tags_first = retrieve_precedents(case, pool).served[0].precedent.precedent_id

    special = next(p for p in pool if p.precedent_id != tags_first and p.category is case.dispute.category)
    pool = [p.model_copy(update={"case_summary": p.case_summary + " The calls went unanswered."}) if p.precedent_id == special.precedent_id else p for p in pool]
    result = retrieve_precedents(case, pool, mode="embeddings", embedder=FakeEmbedder(), query_text="the calls went unanswered")

    assert result.mode_used == "embeddings"
    assert result.served[0].precedent.precedent_id == special.precedent_id


def test_without_an_embedding_model_retrieval_falls_back_to_tags_and_says_so():
    result = retrieve_precedents(a_sealed_case("DISP-002"), seeded_precedents(), mode="embeddings", embedder=None)

    assert result.mode_used == "tags"
    assert "embedding model" in result.note and "tags" in result.note


def test_a_model_that_fails_while_embedding_falls_back_too():
    class Broken:
        def embed(self, texts):
            raise RuntimeError("model file missing")

    result = retrieve_precedents(a_sealed_case("DISP-002"), seeded_precedents(), mode="embeddings", embedder=Broken())

    assert result.mode_used == "tags" and result.served and "model file missing" in result.note


# --- Safety Incidents -------------------------------------------------------------------------------------------------------------


def test_the_store_has_precedents_for_all_three_categories_the_system_resolves():
    assert {p.category for p in seeded_precedents()} >= {DisputeCategory.NO_SHOW_CHARGE, DisputeCategory.SAFETY_INCIDENT, DisputeCategory.ROUTE_DEVIATION}


def test_a_safety_case_is_described_by_what_the_trip_record_shows_about_speed_alerts_and_complaints():
    assert case_tags(a_sealed_case("DISP-005")) == {"speed_far_above_limit", "speed_alert_raised", "rider_complained_in_chat", "rider_ended_trip_early"}
    assert case_tags(a_sealed_case("DISP-006")) == {"speed_near_limit", "no_alert_raised", "no_complaint_in_chat", "trip_completed"}


def test_a_safety_case_is_not_described_in_no_show_terms():
    assert not case_tags(a_sealed_case("DISP-005")) & {"driver_at_pickup", "free_wait_over", "no_show_threshold_reached"}


def test_the_closest_safety_precedent_comes_first_and_only_safety_ones_are_served():
    strong = retrieve_precedents(a_sealed_case("DISP-005"), seeded_precedents())
    weak = retrieve_precedents(a_sealed_case("DISP-006"), seeded_precedents())

    assert strong.served[0].precedent.precedent_id == "PREC-SF-01" and weak.served[0].precedent.precedent_id == "PREC-SF-02"
    assert {s.precedent.category for s in strong.served + weak.served} == {DisputeCategory.SAFETY_INCIDENT}
    assert "speed alert raised" in strong.served[0].why


def test_no_show_cases_are_not_served_safety_precedents():
    result = retrieve_precedents(a_sealed_case("DISP-003"), seeded_precedents())

    assert all(s.precedent.category is DisputeCategory.NO_SHOW_CHARGE for s in result.served)


# --- Route Deviation and Property Damage -----------------------------------------------------------------------------------


def test_a_route_deviation_case_is_described_by_route_length_and_whether_a_detour_was_agreed():
    assert case_tags(a_sealed_case("DISP-008")) == {"route_longer_than_expected", "no_agreed_detour"}
    assert case_tags(a_sealed_case("DISP-009")) == {"route_longer_than_expected", "agreed_detour"}
    assert case_tags(a_sealed_case("DISP-010")) == {"route_longer_than_expected", "no_agreed_detour"}


def test_route_deviation_precedents_are_retrievable_and_point_the_right_way():
    rider_wins = retrieve_precedents(a_sealed_case("DISP-008"), seeded_precedents())
    driver_wins = retrieve_precedents(a_sealed_case("DISP-009"), seeded_precedents())

    assert rider_wins.served[0].precedent.precedent_id == "PREC-RD-01"
    assert driver_wins.served[0].precedent.precedent_id == "PREC-RD-02"
    assert {s.precedent.category for s in rider_wins.served + driver_wins.served} == {DisputeCategory.ROUTE_DEVIATION}


def test_a_property_damage_case_is_described_by_the_claim_and_the_photo_findings():
    case = a_sealed_case("DISP-011")
    findings = [
        EvidenceItem(evidence_id="EV-PHOTO-1-TIME", source="photo_finding", trip_id=case.dispute.trip_id, side="shared",
                     status="available", derived={"alignment": "outside_window"}),
        EvidenceItem(evidence_id="EV-PHOTO-1-AI", source="photo_finding", trip_id=case.dispute.trip_id, side="shared",
                     status="available", derived={"signal": "none"}),
    ]
    with_photos = case.model_copy(update={"evidence": [*case.evidence, *findings]})

    tags = case_tags(with_photos)
    assert "cleaning_fee_claimed" in case_tags(a_sealed_case("DISP-011"))
    assert {"cleaning_fee_claimed", "photo_outside_window", "photo_no_ai_signal"} <= tags
