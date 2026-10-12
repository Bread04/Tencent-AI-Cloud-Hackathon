"""Rebuild curated public DISP-005–007 projections without altering source cases."""

import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
START = "  // Remaining report samples: public projections begin."
END = "  // Remaining report samples: public projections end."


def project(number):
    case_id = f"DISP-{number:03}"
    record = json.loads((ROOT / f"data/cases/{case_id.lower()}.json").read_text(encoding="utf-8"))
    trip, dispute = record["trip"], record["dispute"]
    safety = number in (5, 6)
    category = "Safety / conduct" if safety else "No-show / cancellation"
    # Only public app events are curated here. Driver telemetry and private party
    # statements/history never enter these projections.
    booking = next((event for event in record["app_events"] if event["event_type"] == "booking_confirmed"), None)
    if booking is None:
        raise ValueError(f"{case_id} has no booking_confirmed event.")
    events = [{"id": f"EV-{number:03}-1", "timestamp": booking["timestamp"],
               "title": "Booking confirmed", "detail": f"{trip['pickup_location']['name']} to {trip['dropoff_location']['name']}. Scheduled pickup {trip['scheduled_time'][11:16]}."}]
    if safety:
        event = next(event for event in record["app_events"] if event["event_type"] == ("trip_ended_early" if number == 5 else "trip_completed"))
        events.append({"id": f"EV-{number:03}-2", "timestamp": event["timestamp"],
                       "title": "Trip ended early" if number == 5 else "Trip completed", "detail": event["details"]})
        receipt = None
    else:
        titles = {"driver_arrived": "Arrival notification", "wait_timer_started": "Wait timer started",
                  "wait_timer_expired": "Free wait elapsed", "cancellation_fee_applied": "Cancellation fee charged"}
        for event in record["app_events"][1:]:
            detail = "The app recorded driver arrival. This does not independently verify physical presence." if event["event_type"] == "driver_arrived" else event["details"]
            events.append({"id": f"EV-{number:03}-{len(events)+1}", "timestamp": event["timestamp"], "title": titles[event["event_type"]], "detail": detail})
        amount, currency = float(trip["cancellation_fee"]), trip["currency"]
        receipt = {"id": "RECEIPT-09950", "currency": currency, "total": amount,
                   "method": "Simulated payment", "timestamp": trip["cancellation_time"], "lines": [{"label": "Cancellation fee", "amount": amount}]}
    return {"id": trip["trip_id"], "riderId": trip["rider_id"], "date": trip["scheduled_time"][:10], "time": trip["scheduled_time"][11:16],
            "pickup": trip["pickup_location"]["name"], "destination": trip["dropoff_location"]["name"],
            "status": {5: "Ended early", 6: "Completed", 7: "Cancelled"}[number], "service": "RydeX · simulated", "category": category,
            "fixture": f"{case_id} · curated public source projection",
            "sampleReport": {"id": case_id, "category": category, "summary": "Report unsafe driving" if safety else "Dispute of SGD 5.00 no-show cancellation fee",
                             "statement": dispute["description"], "incidentTime": "",
                             "categoryDetails": {"safetyType": "Unsafe driving"} if safety else {"situation": "A no-show / cancellation fee was charged", "waiting": "10"},
                             "requestedResolution": {"type": "Other", "details": dispute["requested_remedy"]} if safety else {"type": "Refund", "amount": amount, "currency": currency}},
            "receipt": receipt,
            "messages": [{"id": f"MSG-{number:03}-{index}", "timestamp": message["timestamp"], "sender": message["sender"].title(),
                          "type": message["type"], "text": message["content"]}
                         for index, message in enumerate(record["chat_logs"], 1) if message["sender"] in ("rider", "driver")],
            "events": events, "riderLocations": [], "locationNote": f"{case_id} supplies no rider-device location records. Driver telemetry is not rider GPS."}


def main():
    projections = [project(number) for number in (5, 6, 7)]
    riders = [{"id": "R-7830", "name": "Demo rider R-7830", "initials": "R5"},
              {"id": "R-7831", "name": "Demo rider R-7831", "initials": "R6"}]
    data_path = ROOT / "prototypes/ryde-app/data.js"
    source = data_path.read_text(encoding="utf-8")
    marker = "  // Ticket 06 public projections (generated from simulated source cases)."
    if source.count(START) != source.count(END) or source.count(START) > 1:
        raise ValueError("Expected zero or one complete remaining-samples marker pair.")
    if source.count(START) == 1:
        start, end = source.index(START), source.index(END)
        if end < start:
            raise ValueError("Remaining-samples markers are out of order.")
        source = source[:start].rstrip("\r\n") + "\n\n" + source[end + len(END):].lstrip("\r\n")
    if source.count(marker) != 1:
        raise ValueError("Expected exactly one Ticket 06 insertion marker.")
    block = START + "\n  riders.push(..." + json.dumps(riders, indent=2, ensure_ascii=False) + ");\n  trips.push(..." + json.dumps(projections, indent=2, ensure_ascii=False) + ");\n" + END + "\n"
    source = source.replace(marker, block + marker, 1)
    catalog_path = ROOT / "data/prototype/rider-catalog.json"
    # Validate both staged outputs before replacing either checked-in file.
    with TemporaryDirectory() as temp_dir:
        candidate = Path(temp_dir) / "data.js"
        candidate.write_text(source, encoding="utf-8")
        catalog = json.loads(subprocess.check_output(["node", "-e",
            "const d=require(process.argv[1]);process.stdout.write(JSON.stringify({riders:d.riders(),trips:d.riders().flatMap(r=>d.trips(r.id))}));",
            str(candidate)], cwd=ROOT, encoding="utf-8"))
    existing = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog.update({key: existing[key] for key in ("schema_version", "simulated") if key in existing})
    catalog_text = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    data_path.write_text(source, encoding="utf-8")
    catalog_path.write_text(catalog_text, encoding="utf-8")


if __name__ == "__main__":
    main()
