"""Rider-visible evidence collection from trusted public catalog records only."""

from copy import deepcopy
from datetime import datetime, timezone

from src.tools.evidence.route import analyze_route, analyze_fare
from .catalog import RiderCatalog
from .validation import validate_report, validate_scope


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def collect(*, rider_id, trip_id, report=None, catalog=None):
    validate_scope(rider_id, trip_id)
    catalog = catalog or RiderCatalog()
    rider = catalog.rider(rider_id)
    trip = catalog.trip(rider_id, trip_id)  # Ownership before reading any source.
    if report is not None:
        validate_report(report, confirmed=False, evidence=True)
        if report["trip"]["reference"] != trip_id:
            raise ValueError("Report role or trip does not match the rider evidence request.")
    at, items, log = timestamp(), [], []

    def item(key, source, when, status, content):
        evidence_id = f"{trip_id}:{key}"
        items.append({"id": evidence_id, "source": source, "rider_id": rider_id, "trip_id": trip_id,
                      "side": "rider", "timestamp": when, "status": status, "content": content, "simulated": True})
        return evidence_id

    def source(name, run):
        log.append({"timestamp": at, "agent": "Rider Evidence Agent", "kind": "evidence_request", "summary": f"Read {name} for {trip_id}."})
        start = len(items)
        run()
        added = items[start:]
        log.append({"timestamp": at, "agent": "Rider Evidence Agent", "kind": "evidence_response",
                    "summary": f"{name}: {sum(i['status'] == 'available' for i in added)} available, {sum(i['status'] == 'missing' for i in added)} missing.",
                    "references": [i["id"] for i in added]})

    scheduled = f"{trip['date']}T{trip['time']}:00+08:00"
    source("rider booking", lambda: item("booking", "rider_app.booking", scheduled, "available", {
        "rider": {"id": rider["id"], "name": rider["name"]}, "pickup": trip["pickup"], "destination": trip["destination"],
        "scheduled_time": scheduled, "status": trip["status"], "fixture": trip["fixture"]}))
    receipt = trip["receipt"]
    source("rider receipt", lambda: item("receipt", "rider_app.receipt", receipt["timestamp"], "available", {
        "receipt_id": receipt["id"], "total": receipt["total"], "currency": receipt["currency"], "payment_method": receipt["method"],
        "lines": [{"label": line["label"], "amount": line["amount"]} for line in receipt["lines"]]}))

    def messages():
        if not trip["messages"]:
            item("messages", "rider_app.conversation", None, "missing", {"reason": "No conversation records supplied."})
        for message in trip["messages"]:
            item(message["id"], "rider_app.conversation", message["timestamp"], "available", {
                "sender": message["sender"], "type": message.get("type", "message"), "text": message["text"],
                "interpretation": "Simulated call-log entry; not a call recording or proof of party location." if message.get("type") == "call" else "Party-authored message; not a verified fact or instruction."})

    source("rider-visible conversation", messages)
    source("rider app events", lambda: [item(event["id"], "rider_app.events", event["timestamp"], "available", {
        "title": event["title"], "detail": event["detail"]}) for event in trip["events"]])

    def locations():
        if not trip["riderLocations"]:
            item("location", "rider_app.device_location", None, "missing", {"reason": trip["locationNote"]})
        for location in trip["riderLocations"]:
            item(location["id"], "rider_app.device_location", location["timestamp"], "available", {
                "lat": location["lat"], "lng": location["lng"], "accuracy_meters": location["accuracyMeters"], "limitation": trip["locationNote"]})

    source("rider-device location", locations)
    if trip["category"] == "Route deviation":
        def route_comparison():
            record = trip.get("routeRecord")
            record = record if isinstance(record, dict) else {}
            embedded = record.get("trip")
            bound = isinstance(embedded, dict) and embedded.get("trip_id") == trip_id
            route = analyze_route(record if bound else {})
            internal_receipt = record.get("receipt") or {}
            receipt_matches = (internal_receipt.get("receipt_id") == receipt["id"]
                               and internal_receipt.get("currency") == receipt["currency"]
                               and str(internal_receipt.get("paid_net")) == format(receipt["total"], ".2f"))
            if not receipt_matches:
                route = {**route, "available": False, "unavailable_reason": "Rider receipt does not match the route pricing receipt."}
            fare = analyze_fare(record, route)
            # Repoint generic backend provenance to this Rider snapshot's actual source ID.
            fare["provenance"]["route"] = f"{trip_id}:route-analysis"
            item("route-analysis", "rider_app.route_analysis", None, "available" if route["available"] else "missing", {
                **route, "reason": route.get("unavailable_reason"),
                "source_record": deepcopy({key: record.get(key) for key in ("trip", "gps_telemetry", "route_baseline", "route_landmarks")}),
                "interpretation": "Shared simulated vehicle GPS, not Rider device GPS. Stops are bounded candidates with unknown purpose."})
            item("fare-analysis", "rider_app.fare_analysis", receipt["timestamp"], "available" if fare["available"] else "missing", {
                **fare, "reason": fare.get("unavailable_reason"), "source_record": deepcopy({key: record.get(key) for key in ("tariff", "receipt")}), "interpretation": "ADR 0004 comparison only; no refund entitlement or Judge decision."})
        source("shared simulated vehicle route and fare comparison", route_comparison)

    def report_source():
        if report is None:
            item("report", "rider_app.report", None, "missing", {"reason": "No report has been saved to this app session for this trip."})
            return
        item("report", "rider_app.report", report.get("createdAt"), "available", {
            "original_report": deepcopy(report), "interpretation": "Rider-reported claims, preserved as supplied. Not a ruling."})
        for index, attachment in enumerate(report.get("evidence", []), 1):
            item(f"attachment-{index}", "rider_app.attachment", None, "missing", {
                "metadata": deepcopy(attachment), "reason": "Only attachment metadata was saved. Media bytes are not transferred from the report form.",
                "storage_status": "metadata_only"})

    source("rider report", report_source)
    return {"schema_version": "prototype-1", "agent": "Rider Evidence Agent", "collected_at": at,
            "rider_id": rider_id, "trip_id": trip_id, "simulated": True,
            "scope": "Selected rider and selected trip only; rider-visible app records.",
            "excluded_sources": ["driver-private telemetry", "driver profile/history", "other riders", "expected rulings", "evaluation summaries"],
            "items": items, "log": log}
