"""Build the three explicitly simulated source cases and public Rider projections.

This authoring script is not a runtime classifier. Evaluation labels are written
separately and are never copied into browser data or model prompts.
"""
import json
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from src.tools.evidence.route import analyze_route

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    (ROOT / path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    projections = []
    start = (1.299, 103.855)
    stop = (1.307, 103.863)
    finish = (1.283, 103.860)
    for number in (8, 9, 10):
        dispute_id = f"DISP-{number:03}"
        trip_id = f"TRIP-2026-ROUTE-{number:03}"
        at = datetime.fromisoformat(f"2026-09-{8+number:02}T14:00:00+08:00")
        stamp = lambda minute: (at + timedelta(minutes=minute)).isoformat()
        points = []
        for minute in range(21):
            if minute <= 5:
                ratio, a, b = minute / 5, start, stop
            elif minute <= 8:
                ratio, a, b = 0, stop, stop
            else:
                ratio, a, b = (minute - 8) / 12, stop, finish
            points.append({"timestamp": stamp(minute), "lat": round(a[0] + (b[0]-a[0])*ratio, 7),
                           "lng": round(a[1] + (b[1]-a[1])*ratio, 7)})
        baseline = {"source_id": f"BASELINE-{number:03}", "simulated": True, "expected_minutes": "12.00",
                    "points": [{"lat": start[0], "lng": start[1]}, {"lat": 1.291, "lng": 103.858}, {"lat": finish[0], "lng": finish[1]}]}
        statements = {
            8: ("The trip went via Lavender MRT and stopped for three minutes. I did not ask for that detour. Please refund the full fare.",
                "I missed the turn and stopped near Lavender MRT to check the route. The Rider did not request that detour.",
                [("rider", "Why are we near Lavender MRT? I did not request this detour."), ("driver", "I missed the turn and stopped to check the route. Sorry about the extra distance.")]),
            9: ("The trip was longer than the app baseline and cost more. Please refund the full fare.",
                "The Rider requested a detour via Lavender MRT with a three-minute stop, then Marina Bay Sands. I followed that request.",
                [("rider", "Please detour via Lavender MRT and stop there for three minutes so I can collect my bag, then continue to Marina Bay Sands."), ("driver", "Yes, I can take that detour and stop for three minutes. The fare may increase."), ("rider", "Understood, please go ahead.")]),
            10: ("The Driver took a longer route via Lavender MRT and stopped. I remember discussing the route but I am not sure we agreed to that detour. Please review the full fare.",
                "I understood the conversation as agreement to the Lavender route, and there was traffic ahead. There is no independent traffic record in this simulated case.",
                [("driver", "There may be traffic ahead. We could go via Lavender MRT."), ("rider", "Would that work? I need to get there soon."), ("driver", "I will try that road.")]),
        }
        description, driver, messages = statements[number]
        record = {"_simulated": "Simulated road geometry, receipt, tariff and party messages; not a real Ryde trip.",
                  "dispute": {"dispute_id": dispute_id, "trip_id": trip_id, "filed_by": "rider", "category": "route_deviation",
                              "description": description, "requested_remedy": "Refund the full paid trip fare", "filed_at": stamp(35), "photos": [], "driver_statement": driver},
                  "trip": {"trip_id": trip_id, "rider_id": "R-7823", "driver_id": f"D-ROUTE-{number}",
                           "pickup_location": {"name": "Bugis Junction", "lat": start[0], "lng": start[1]},
                           "dropoff_location": {"name": "Marina Bay Sands", "lat": finish[0], "lng": finish[1]},
                           "scheduled_time": stamp(0), "started_at": stamp(0), "completed_at": stamp(20), "currency": "SGD"},
                  "gps_telemetry": points, "route_baseline": baseline,
                  "route_landmarks": [{"id": "LANDMARK-LAVENDER-MRT", "name": "Lavender MRT", "lat": stop[0], "lng": stop[1]}],
                  "tariff": {"base": "3.00", "km_rate": "1.20", "minute_rate": "0.25", "surge": "1.20", "booking": "0.80", "tolls": "1.00", "promo": "2.00"},
                  "chat_logs": [{"id": f"MSG-{number:03}-{i+1}", "timestamp": stamp((9+i) if number == 8 else (-3+i)), "sender": sender, "type": "message", "content": message} for i,(sender,message) in enumerate(messages)],
                  "app_events": [{"id": f"APP-{number:03}-1", "timestamp": stamp(20), "event_type": "trip_completed", "details": "Simulated trip completed. Vehicle GPS is supplied separately; no Rider device GPS was recorded."}],
                  "rider_history": {"dispute_history": {"total_disputes": 0, "rejected": 0}}, "driver_history": {"dispute_history": {"total_disputes": 0, "rejected": 0}}}
        route = analyze_route(record)
        tariff = {key: Decimal(value) for key, value in record["tariff"].items()}
        paid = ((tariff["base"] + Decimal(route["actual_km"])*tariff["km_rate"] + Decimal(route["actual_minutes"])*tariff["minute_rate"])*tariff["surge"] + tariff["booking"] + tariff["tolls"] - tariff["promo"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        record["receipt"] = {"receipt_id": f"RECEIPT-{number:03}", "trip_id": trip_id, "paid_net": str(paid), "currency": "SGD", "timestamp": stamp(20)}
        record["trip"]["paid_net"] = str(paid)
        write(f"data/cases/disp-{number:03}.json", record)
        from src.tools.evidence.route import analyze_fare
        fare = analyze_fare(record, route)
        result = {8: ("partially_uphold", "claimant", "partial_refund", "clear"), 9: ("reject", "respondent", "no_action", "clear"), 10: ("reject", "balanced", "no_action", "arguable")}[number]
        outcome, balance, remedy, fit = result
        reason = {
            8: "Vehicle GPS establishes excess route distance and a bounded three-minute stop candidate. MSG-008-2 admits a missed turn and route-check stop, matching the reported excess; MSG-008-1 disputes consent. The full fare requested is not justified: ADR 0004 limits the refund to the code-computed excess net fare.",
            9: 'EV-CHAT-1 MSG-009-1 records the exact Rider request: "'+messages[0][1]+'" MSG-009-3 confirms it. The vehicle route and three-minute stop candidate match that specific detour; consent does not extend to any other route change. Excess alone does not establish an overcharge. Reject the refund claim.',
            10: "EV-CHAT-1 MSG-010-2 asks whether the route would work; it is not an explicit request or clear agreement to the observed detour and stop. The Driver's traffic explanation has no independent supporting record. Distance alone cannot resolve these competing accounts. The evidence is balanced: hold this proposal for review, with no authorised amount.",
        }[number]
        common = ["EV-ROUTE-1", "EV-FARE-1", "EV-CHAT-1"]
        rider_counter = "The Driver may have a justified route change or a Rider request."
        rider_answer = {8: "The Driver's own MSG-008-2 attributes the detour to a missed turn, and MSG-008-1 disputes consent. Ask only for the supported excess-fare remedy, not an automatic full refund.",
                        9: 'MSG-009-1 says "'+messages[0][1]+'" and MSG-009-3 agrees. That exact request seriously weakens the Rider claim despite the longer route.',
                        10: "The Driver mentions traffic, but no traffic record was supplied. The Rider's question is ambiguous; ask for clarification instead of claiming proven fault."}[number]
        driver_claim = {8: "The Driver acknowledges a missed turn and route-check stop, while opposing a refund of the legitimate baseline fare.",
                        9: 'The Driver followed EV-CHAT-1 MSG-009-1: "'+messages[0][1]+'" and MSG-009-3 confirmation. The requested Lavender detour and stop match the vehicle route.',
                        10: "The Driver understood the route conversation as agreement and cites traffic, but neither consent nor traffic is independently established."}[number]
        stub = {"_simulated": "Public, case-specific scripted replies; no private evaluation labels.",
                "rider_advocate": {"author": "rider_advocate", "claim_restated": description, "facts_relied_on": common, "missing_evidence_ids": ["EV-RIDERLOC-1"], "counter_arguments": [{"argument": rider_counter, "response": rider_answer}], "policy_clause_ids": ["R-04", "D-04", "R-03", "D-03"], "requested_outcome": "Review the original full-fare request against consent and ADR 0004; grant only any supported excess-fare refund."},
                "driver_advocate": {"author": "driver_advocate", "claim_restated": driver_claim, "facts_relied_on": common, "missing_evidence_ids": ["EV-RIDERLOC-1"], "counter_arguments": [{"argument": "The Rider points to the excess distance, duration and charge.", "response": {8: "The excess is supported, and the Driver acknowledges the missed turn. A partial refund can preserve the legitimate optimal fare under ADR 0004.", 9: "The exact Rider request and confirmation match this detour. Excess metrics alone do not invalidate a requested detour.", 10: "The metrics support review but not an inference of consent or fault. The competing explanations need human clarification."}[number]}], "policy_clause_ids": ["R-04", "D-04", "R-03", "D-03"], "requested_outcome": {8: "Limit any refund to supported excess net fare.", 9: "Reject the refund claim for the specifically requested detour.", 10: "Hold the competing accounts for human review."}[number]},
                "judge": {"outcome": outcome, "balance_of_evidence": balance, "remedy": remedy, "policy_fit": fit, "policy_fit_reason": "Route communication and fare review clauses apply; ADR 0004 supplies arithmetic without changing policy text.", "cited_evidence_ids": common, "cited_policy_clause_ids": ["R-04", "D-04", "R-03", "D-03"], "reasoning_summary": reason, "amount_input_evidence_ids": ["EV-ROUTE-1", "EV-FARE-1"] if number == 8 else [],
                          "argument_assessments": [{"ref": f"{agent}#{argument}", "verdict": "unproven" if number == 10 else ("not_decisive" if number == 9 and agent == "rider_advocate" else "accepted"), "reason": reason, "evidence_ids": common} for agent in ("rider_advocate", "driver_advocate") for argument in ("claim", "counter-1")]},
                "judge_self_check": {"supported": True, "problems": []}}
        # The prepared route cases stay stable when main's second-pass switch is enabled.
        stub["judge_second_pass"] = deepcopy(stub["judge"])
        for side in ("rider", "driver"):
            index = next(i for i, message in enumerate(record["chat_logs"], 1) if message["sender"] == side)
            message = record["chat_logs"][index-1]
            stub[f"{side}_evidence_agent"] = {"facts": [{"source_ref": f"EV-CHAT-1#{index}", "quote": message["content"], "fact": f"The {side} wrote: {message['content']}"}]}
        write(f"fixtures/stub/{dispute_id}.json", stub)
        evaluation = {"dispute_id": dispute_id, "scenario_classification": {8: "rider_wins", 9: "driver_wins", 10: "ambiguous"}[number], "expected_review_required": number == 10, "expected_summary": f"Evaluation-only Route Deviation label {dispute_id}: " + {8: "supported excess fare, partial remedy", 9: "specific agreed detour, no remedy", 10: "unresolved consent, human review"}[number], "expected_outcome": outcome, "expected_remedy": remedy, "expected_status": "proposal" if number == 10 else "final"}
        if number == 8:
            evaluation["expected_amount"] = fare["refund"]
        if number == 10:
            evaluation["expected_outcome"] = None
            evaluation["expected_remedy"] = None
            evaluation["acceptable_review_triggers"] = ["balanced_evidence"]
        write(f"data/cases/disp-{number:03}.eval.json", evaluation)
        projection = {"id": trip_id, "riderId": "R-7823", "date": stamp(0)[:10], "time": "14:00", "pickup": "Bugis Junction", "destination": "Marina Bay Sands", "status": "Completed", "service": "RydeX · simulated", "category": "Route deviation", "fixture": dispute_id+" · curated public source projection",
                      "sampleReport": {"id": dispute_id, "category": "Route deviation", "summary": "Review the route and full paid fare", "statement": description, "incidentTime": stamp(0)[:16], "categoryDetails": {"route": "Bugis Junction to Marina Bay Sands", "deviation": "Via Lavender MRT with a stop", "agreement": {8: "No", 9: "Yes", 10: "Not sure"}[number]}},
                      "receipt": {"id": record["receipt"]["receipt_id"], "currency": "SGD", "total": float(paid), "method": "E-wallet", "timestamp": stamp(20), "lines": [
                          {"label": f"{label} (surge ×{tariff['surge']})", "amount": float((Decimal(fare["breakdown"][key])*tariff["surge"]).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))}
                          for label,key in [("Base fare","base"),("Distance fare","distance"),("Time fare","time")]
                      ] + [{"label": "Booking fee", "amount": float(tariff["booking"])}, {"label": "Tolls", "amount": float(tariff["tolls"])}, {"label": "Promotion", "amount": -float(tariff["promo"])}]},
                      "messages": [{"id": message["id"], "timestamp": message["timestamp"], "sender": message["sender"].title(), "text": message["content"]} for message in record["chat_logs"]],
                      "events": [{"id": event["id"], "timestamp": event["timestamp"], "title": "Trip completed", "detail": event["details"]} for event in record["app_events"]],
                      "riderLocations": [], "locationNote": "No Rider device GPS was recorded. Shared simulated vehicle GPS is labelled separately.",
                      "routeRecord": {key: record[key] for key in ("trip", "gps_telemetry", "route_baseline", "route_landmarks", "tariff", "receipt")}}
        projections.append(projection)
    data_path = ROOT / "prototypes/ryde-app/data.js"
    source = data_path.read_text(encoding="utf-8")
    marker = "  // Ticket 06 public projections (generated from simulated source cases)."
    if marker in source:
        source = source[:source.index(marker)] + source[source.index("  const clone =", source.index(marker)):]
    source = source.replace("  const clone =", marker + "\n  trips.push(..." + json.dumps(projections, indent=2) + ");\n  const clone =", 1)
    data_path.write_text(source, encoding="utf-8")
    # Keep the trusted Python catalog synchronized with the same curated projections.
    # Existing public app records were extracted once with Node, without private data.
    catalog_path = ROOT / "data/prototype/rider-catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    route_ids = {trip["id"] for trip in projections}
    catalog["trips"] = [trip for trip in catalog["trips"] if trip["id"] not in route_ids] + projections
    rider_order = {rider["id"]: index for index, rider in enumerate(catalog["riders"])}
    catalog["trips"].sort(key=lambda trip: rider_order[trip["riderId"]])
    write("data/prototype/rider-catalog.json", catalog)


if __name__ == "__main__":
    main()
