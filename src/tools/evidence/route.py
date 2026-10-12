"""Simulated vehicle-route and fare arithmetic; no inference of consent or fault.

ADR 0004 fixes precision, gap and stop assumptions. Raw records stay citable in
the sealed Case; prompts receive the bounded derived summary only.
"""

from datetime import datetime
from decimal import Decimal, DecimalException, InvalidOperation, ROUND_HALF_UP
from math import asin, cos, isfinite, radians, sin, sqrt

from src.contracts import EvidenceItem

ADR = "docs/adr/0004-route-deviation-refund-rule.md"
CENT = Decimal("0.01")


def rounded(value, precision):
    return Decimal(str(value)).quantize(Decimal(precision), rounding=ROUND_HALF_UP)


def metres(a, b):
    lat1, lat2 = radians(a["lat"]), radians(b["lat"])
    dlat, dlng = lat2 - lat1, radians(b["lng"] - a["lng"])
    return 2 * 6371000 * asin(min(1, sqrt(sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2)))


def _points(points, timed=False):
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError("Insufficient path: at least three sampled route points are required; endpoints alone cannot establish a travelled route.")
    previous = None
    for point in points:
        if not isinstance(point, dict):
            raise ValueError("Invalid route point.")
        for key, bound in (("lat", 90), ("lng", 180)):
            value = point.get(key)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value) or abs(value) > bound:
                raise ValueError("Invalid route coordinates.")
        if timed:
            now = datetime.fromisoformat(point["timestamp"])
            if now.utcoffset() is None:
                raise ValueError("Route timestamps need a timezone.")
            if previous is not None and now <= previous:
                raise ValueError("Route timestamps must increase.")
            previous = now
    return points


def _gap(a, b):
    return b.get("gap_before") is True or (datetime.fromisoformat(b["timestamp"]) - datetime.fromisoformat(a["timestamp"])).total_seconds() > 120


def stop_candidates(points):
    """Disjoint observed clusters, with neither endpoint dwell nor gap bridging."""
    candidates, start = [], 0

    def finish(end):
        first, last = points[start], points[end]
        seconds = (datetime.fromisoformat(last["timestamp"]) - datetime.fromisoformat(first["timestamp"])).total_seconds()
        if seconds >= 120 and all(metres(point, endpoint) > 50 for point in points[start:end+1] for endpoint in (points[0], points[-1])):
            candidates.append({"start": first["timestamp"], "end": last["timestamp"], "observed_seconds": seconds,
                               "lat": first["lat"], "lng": first["lng"], "purpose": "unknown"})

    for index in range(1, len(points)):
        if _gap(points[index - 1], points[index]) or metres(points[start], points[index]) > 25:
            finish(index - 1)
            start = index
    finish(len(points) - 1)
    return candidates


def analyze_route(record):
    result = {"analysis_adr": ADR, "vehicle_gps_only": True, "baseline": "supplied simulated road baseline",
              "limitations": ["Distance does not establish fault or consent. Stop purpose is unknown."]}
    try:
        if not isinstance(record, dict):
            raise ValueError("Missing or invalid route record.")
        actual = _points(record.get("gps_telemetry"), timed=True)
        baseline = record.get("route_baseline")
        if not isinstance(baseline, dict):
            raise ValueError("Missing or invalid route baseline.")
        optimal = _points(baseline.get("points"))
        trip = record["trip"]
        for point, endpoint in ((actual[0], trip["pickup_location"]), (actual[-1], trip["dropoff_location"])):
            _points([endpoint, endpoint, endpoint])
            if metres(point, endpoint) > 50:
                raise ValueError("Route endpoints do not match the booked trip.")
        started, completed = datetime.fromisoformat(trip["started_at"]), datetime.fromisoformat(trip["completed_at"])
        if started.utcoffset() is None or completed.utcoffset() is None or started >= completed:
            raise ValueError("Invalid trip start/completion times.")
        if datetime.fromisoformat(actual[0]["timestamp"]) != started or datetime.fromisoformat(actual[-1]["timestamp"]) != completed:
            raise ValueError("Telemetry does not cover the complete trip.")
        result.update(trip_id=trip["trip_id"], started_at=trip["started_at"], completed_at=trip["completed_at"])
        gaps = sum(_gap(a, b) for a, b in zip(actual, actual[1:]))
        result.update(stop_candidates=stop_candidates(actual), telemetry_gaps=gaps)
        if gaps:
            raise ValueError("Telemetry gaps: unknown path and dwell are not bridged; route comparison unavailable.")
        actual_km = rounded(sum(metres(a, b) for a, b in zip(actual, actual[1:])) / 1000, "0.001")
        optimal_km = rounded(sum(metres(a, b) for a, b in zip(optimal, optimal[1:])) / 1000, "0.001")
        if actual_km <= 0 or optimal_km <= 0:
            raise ValueError("Route distance must be positive.")
        # Same declared endpoints are required for a meaningful comparison.
        if metres(actual[0], optimal[0]) > 50 or metres(actual[-1], optimal[-1]) > 50:
            raise ValueError("Baseline endpoints do not match the travelled route.")
        duration = rounded((datetime.fromisoformat(actual[-1]["timestamp"]) - datetime.fromisoformat(actual[0]["timestamp"])).total_seconds() / 60, "0.01")
        expected = _number(record["route_baseline"]["expected_minutes"], positive=True)
        expected = rounded(expected, "0.01")
        if expected <= 0:
            raise ValueError("Expected duration must be positive after rounding.")
        result.update(actual_km=str(actual_km), optimal_km=str(optimal_km), excess_km=str(max(Decimal(0), actual_km - optimal_km)),
                      actual_minutes=str(duration), expected_minutes=str(expected), excess_minutes=str(max(Decimal(0), duration - expected)),
                      provenance={"actual": "gps_telemetry", "optimal": "route_baseline.points", "expected_minutes": "route_baseline.expected_minutes"}, available=True)
        result["landmark_observations"] = []
        for landmark in record.get("route_landmarks", []):
            _points([landmark, landmark, landmark])
            nearest = min(actual, key=lambda point: metres(point, landmark))
            distance = rounded(metres(nearest, landmark), "0.1")
            result["landmark_observations"].append({"id": landmark["id"], "name": landmark["name"],
                "within_50m": distance <= 50, "nearest_sample_at": nearest["timestamp"], "distance_m": str(distance),
                "source": "supplied simulated route_landmarks matched to gps_telemetry"})
    except (KeyError, TypeError, ValueError, DecimalException, OverflowError) as error:
        result.update(available=False, unavailable_reason=str(error))
    return result


def _number(value, positive=False):
    if isinstance(value, bool):
        raise ValueError("Invalid numeric input.")
    number = Decimal(str(value))
    if not number.is_finite() or not isfinite(float(number)) or abs(number.as_tuple().exponent) > 1000 or number < 0 or (positive and number <= 0):
        raise ValueError("Fare inputs must be finite and nonnegative; surge/duration must be positive.")
    return number


def analyze_fare(record, route):
    result = {"analysis_adr": ADR, "provenance": {"tariff": "tariff", "receipt": "receipt", "route": "EV-ROUTE-1"}}
    try:
        if not route["available"]:
            raise ValueError("Route comparison unavailable: " + route["unavailable_reason"])
        tariff, receipt = record["tariff"], record["receipt"]
        if receipt["currency"] != "SGD":
            raise ValueError("Receipt must use SGD.")
        if not isinstance(receipt.get("receipt_id"), str) or not receipt["receipt_id"].strip() or receipt.get("trip_id") != route["trip_id"]:
            raise ValueError("Receipt identity and trip association are required.")
        if datetime.fromisoformat(receipt["timestamp"]) != datetime.fromisoformat(route["completed_at"]):
            raise ValueError("Receipt time does not match trip completion.")
        values = {key: _number(tariff[key], positive=(key == "surge")) for key in ("base", "km_rate", "minute_rate", "surge", "booking", "tolls", "promo")}
        paid = _number(receipt["paid_net"])
        if paid != paid.quantize(CENT):
            raise ValueError("Receipt amount must be in SGD cents.")
        def net(km, minutes):
            return max(Decimal(0), (values["base"] + Decimal(km) * values["km_rate"] + Decimal(minutes) * values["minute_rate"]) * values["surge"] + values["booking"] + values["tolls"] - values["promo"])
        actual_net = net(route["actual_km"], route["actual_minutes"])
        if actual_net.quantize(CENT, rounding=ROUND_HALF_UP) != paid:
            raise ValueError("Tariff does not reconcile to the authoritative paid net receipt.")
        optimal_net = net(route["optimal_km"], route["expected_minutes"])
        refund = min(paid, max(Decimal(0), paid - optimal_net)).quantize(CENT, rounding=ROUND_HALF_UP)
        result.update(available=True, currency="SGD", paid_net=str(paid), tariff={key: str(value) for key, value in values.items()},
                      actual_net=str(actual_net), optimal_net=str(optimal_net), refund=str(refund),
                      breakdown={"base": str(values["base"]), "distance": str(Decimal(route["actual_km"]) * values["km_rate"]),
                                 "time": str(Decimal(route["actual_minutes"]) * values["minute_rate"]),
                                 "surge": str(values["surge"]), "booking": str(values["booking"]), "tolls": str(values["tolls"]), "promo": str(values["promo"]), "paid_net": str(paid)})
    except (KeyError, TypeError, ValueError, DecimalException, OverflowError) as error:
        result.update(available=False, unavailable_reason=str(error))
    return result


def gather_route_evidence(trip_id, record):
    route = analyze_route(record)
    fare = analyze_fare(record, route)
    def item(evidence_id, source, analysis, content):
        return EvidenceItem(evidence_id=evidence_id, source=source, trip_id=trip_id, side="shared",
                            status="available" if analysis["available"] else "missing", derived=analysis, content=content)
    return [item("EV-ROUTE-1", "route", route, {key: record.get(key) for key in ("trip", "gps_telemetry", "route_baseline", "route_landmarks")}),
            item("EV-FARE-1", "fare", fare, {"tariff": record.get("tariff"), "receipt": record.get("receipt")})]
