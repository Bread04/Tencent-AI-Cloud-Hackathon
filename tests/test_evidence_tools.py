"""Seam: gather_evidence(trip_id, catalog) -> Evidence Items for one Trip."""

import copy

from src.contracts import EvidenceStatus
from src.intake import Catalog, load_catalog
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


def test_the_wait_is_counted_from_the_drivers_arrival_not_the_scheduled_time():
    fare = evidence_by_source()["fare"]

    # Arrived 08:43, scheduled 08:45, cancelled 08:51: 8 minutes from arrival (6 from the scheduled time).
    assert fare.derived["wait_minutes_from_arrival"] == 8
    assert fare.derived["free_wait_expired"] is True
    assert fare.derived["no_show_threshold_reached"] is True


def test_a_cancellation_before_the_no_show_threshold_is_not_marked_as_reaching_it():
    catalog = load_catalog()
    record = copy.deepcopy(catalog.trip(TRIP))
    record["trip"]["cancellation_time"] = "2026-09-13T08:47:00+08:00"  # 4 minutes after arrival
    early = Catalog(disputes=catalog.disputes, trips={TRIP: record})

    fare = {item.source: item for item in gather_evidence(TRIP, early)}["fare"]

    assert fare.derived["wait_minutes_from_arrival"] == 4
    assert fare.derived["free_wait_expired"] is False
    assert fare.derived["no_show_threshold_reached"] is False
