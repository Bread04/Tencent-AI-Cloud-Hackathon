"""Seam: gather_evidence(trip_id, catalog) -> Evidence Items for one Trip."""

from src.contracts import EvidenceStatus
from src.intake import load_catalog
from src.tools.evidence import gather_evidence

TRIP = "TRIP-2026-09945"  # the cleaned DISP-002 trip


def evidence_by_source():
    return {item.source: item for item in gather_evidence(TRIP, load_catalog())}


def test_a_no_show_trip_yields_gps_chat_fare_and_history_items():
    items = gather_evidence(TRIP, load_catalog())

    assert {"gps", "chat", "fare", "history"} <= {item.source for item in items}
    assert len({item.evidence_id for item in items}) == len(items)
    assert all(item.trip_id == TRIP for item in items)
    assert all(isinstance(item.status, EvidenceStatus) for item in items)


def test_gps_item_carries_arrival_and_wait_values_computed_by_code():
    gps = evidence_by_source()["gps"]

    assert gps.status is EvidenceStatus.AVAILABLE
    assert gps.derived["minutes_at_pickup"] == 8  # sample evidence summary: stationary 08:43 to 08:51
    assert gps.derived["arrival_vs_scheduled_min"] == -2  # arrived 2 min early
    assert gps.derived["distance_to_pickup_at_arrival_m"] < 10


def test_chat_item_counts_contact_attempts_by_each_side():
    chat = evidence_by_source()["chat"]

    assert chat.derived["driver_messages"] == 4
    assert chat.derived["driver_calls"] == 1
    assert chat.derived["rider_messages"] == 0


def test_fare_item_holds_the_fee_and_the_policy_timers():
    fare = evidence_by_source()["fare"]

    assert fare.derived["cancellation_fee"] == "5.00"
    assert fare.derived["currency"] == "SGD"
    assert fare.derived["free_wait_min"] == 5
    assert fare.derived["no_show_threshold_min"] == 8


def test_data_the_system_does_not_have_comes_back_marked_missing_with_a_reason():
    rider_position = evidence_by_source()["rider_location"]  # the sample has no rider-side location

    assert rider_position.status is EvidenceStatus.MISSING
    assert rider_position.content  # says why it is missing
