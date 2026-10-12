"""Evidence tools: turn a Trip record into typed Evidence Items (architecture.md section 5.2).

Plain code, no model. Derived values (arrival against schedule, minutes at the
pickup point, contact attempts) are computed here so advocates and the Judge
all argue from the same numbers. Data the system does not have comes back as
an item with status `missing`, never as an absent item.
"""

from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from src.contracts import EvidenceItem
from src.intake import Catalog


def gather_evidence(trip_id: str, catalog: Catalog) -> list[EvidenceItem]:
    record = catalog.trip(trip_id)
    if record["dispute"]["category"] == "route_deviation":
        from src.tools.evidence.route import gather_route_evidence
        chat = _chat_item(trip_id, record) if isinstance(record.get("chat_logs"), list) and record["chat_logs"] else EvidenceItem(
            evidence_id="EV-CHAT-1", source="chat", trip_id=trip_id, side="shared", status="missing",
            content="No route conversation records were supplied; consent remains unknown.")
        return [*gather_route_evidence(trip_id, record), chat,
                _history_item(trip_id, record), _rider_location_item(trip_id)]
    return [
        _gps_item(trip_id, record),
        _chat_item(trip_id, record),
        _fare_item(trip_id, record),
        _history_item(trip_id, record),
        _rider_location_item(trip_id),
    ]


def _arrival(record: dict) -> dict:
    return next(point for point in record["gps_telemetry"] if point["status"] == "arrived")


def _gps_item(trip_id: str, record: dict) -> EvidenceItem:
    trip, points = record["trip"], record["gps_telemetry"]
    arrival = _arrival(record)
    arrived_at = datetime.fromisoformat(arrival["timestamp"])
    pickup = trip["pickup_location"]
    return EvidenceItem(
        evidence_id="EV-GPS-1",
        source="gps",
        trip_id=trip_id,
        side="driver",
        timestamp=arrived_at,
        status="available",
        content=points,
        derived={
            "arrival_time": arrival["timestamp"],
            "distance_to_pickup_at_arrival_m": round(
                _metres_between(arrival["lat"], arrival["lng"], pickup["lat"], pickup["lng"])
            ),
            "arrival_vs_scheduled_min": _minutes_between(trip["scheduled_time"], arrival["timestamp"]),
            "minutes_at_pickup": _minutes_between(arrival["timestamp"], trip["cancellation_time"]),
        },
    )


def _chat_item(trip_id: str, record: dict) -> EvidenceItem:
    entries = record["chat_logs"]

    def count(sender: str, kind: str) -> int:
        return sum(1 for entry in entries if entry["sender"] == sender and entry["type"] == kind)

    return EvidenceItem(
        evidence_id="EV-CHAT-1",
        source="chat",
        trip_id=trip_id,
        side="shared",
        status="available",
        content=entries,
        derived={
            "driver_messages": count("driver", "message"),
            "driver_calls": count("driver", "call"),
            "rider_messages": count("rider", "message"),
        },
    )


def _fare_item(trip_id: str, record: dict) -> EvidenceItem:
    trip, policy = record["trip"], record["cancellation_policy"]
    # The policy sets no wait time (see src/agents/policy), so the trip's own thresholds decide.
    # The clock starts when the driver arrives at the pickup point, not at the scheduled time.
    waited = _minutes_between(_arrival(record)["timestamp"], trip["cancellation_time"])
    return EvidenceItem(
        evidence_id="EV-FARE-1",
        source="fare",
        trip_id=trip_id,
        side="shared",
        timestamp=datetime.fromisoformat(trip["cancellation_time"]),
        status="available",
        content=record["app_events"],
        derived={
            "cancellation_fee": trip["cancellation_fee"],
            "currency": trip["currency"],
            "free_wait_min": policy["free_wait_time_min"],
            "no_show_threshold_min": policy["no_show_threshold_min"],
            "wait_minutes_from_arrival": waited,
            "free_wait_expired": waited >= policy["free_wait_time_min"],
            "no_show_threshold_reached": waited >= policy["no_show_threshold_min"],
        },
    )


def _history_item(trip_id: str, record: dict) -> EvidenceItem:
    return EvidenceItem(
        evidence_id="EV-HISTORY-1",
        source="history",
        trip_id=trip_id,
        side="shared",
        status="available",
        content={"rider": record["rider_history"], "driver": record["driver_history"]},
    )


def _rider_location_item(trip_id: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id="EV-RIDERLOC-1",
        source="rider_location",
        trip_id=trip_id,
        side="rider",
        status="missing",
        content="No rider location was recorded for this Trip, so the rider's position is unknown.",
    )


def _minutes_between(start: str, end: str) -> int:
    return round((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 60)


def _metres_between(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    d_lat, d_lng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(a))
