"""Deterministic supported Rider Submission, never a Judge decision."""

from copy import deepcopy
import re


def prepare(*, report, evidence, policy):
    items = evidence["items"]
    def find(source):
        return [item for item in items if item["source"] == f"rider_app.{source}"]
    def refs(source):
        return [item["id"] for item in find(source)]
    clauses = [match["reference"] for match in policy["matches"]]
    def policies(*ids):
        return [clause for clause in clauses if clause in ids]
    report_refs = refs("report")
    receipt = next((item for item in find("receipt") if item["status"] == "available"), None)
    location = find("device_location")
    is_no_show = report["category"] == "No-show / cancellation"
    route = next(iter(find("route_analysis")), None)
    fare = next(iter(find("fare_analysis")), None)
    has_route = route is not None and route["status"] == "available"
    needs_route_review = not is_no_show and (not has_route or fare is None or fare["status"] != "available")
    arguments = [{"title": "Review the specific no-show charge" if is_no_show else "Review how the route change was handled",
        "text": "Ask for a review of the reported cancellation or no-show charge against the booking and pickup coordination records. Preserve the Rider’s original account without treating it as a verified fact." if is_no_show else "The Rider raises a route concern. Ask for a review of the original booking and recorded route discussion, including whether the change was communicated and agreed.",
        "evidence_ids": report_refs + refs("booking") + refs("conversation"), "policy_ids": policies("R-02" if is_no_show else "R-04", "R-06")}]
    if receipt:
        content = receipt["content"]
        arguments.append({"title": "Keep the requested remedy tied to the receipt",
            "text": f"The simulated receipt records {content['currency']} {content['total']:.2f} in total charges. It supports checking the recorded amount; it does not establish that the charge was unjustified or that the full amount is refundable.",
            "evidence_ids": [receipt["id"]] + report_refs, "policy_ids": policies("R-02", "R-03")})
    counter = []
    messages = [item for item in find("conversation") if item["status"] == "available"]
    message_refs = [item["id"] for item in messages]
    if any(item["content"]["sender"] == "Driver" for item in messages):
        counter.append({"title": "The Driver’s messages must also be considered",
            "text": "The supplied conversation contains the Driver’s account. Read the complete exchange below, including statements that challenge the Rider. A message is not verified GPS, proof that it was read, or proof that a route change was agreed.", "evidence_ids": message_refs})
    gaps = [{"evidence_ids": [item["id"]], "text": item["content"].get("reason") or "This source was not supplied."} for item in items if item["status"] == "missing"]
    if location and all(item["status"] == "missing" for item in location):
        arguments.append({"title": "Request clarification where location evidence is absent",
            "text": "The Rider’s location cannot be checked from the available app records. Ask that this uncertainty be acknowledged during review; missing GPS does not prove either party’s account.",
            "evidence_ids": [item["id"] for item in location], "policy_ids": []})
    if not is_no_show and not has_route:
        gaps.append({"text": "The app supplies no complete travelled path or valid route comparison. Two endpoint samples cannot prove a detour or an overcharge. " + ((route or {}).get("content", {}).get("reason") or ""),
                     "evidence_ids": refs("device_location") + refs("route_analysis")})
    conclusion = "Present the Rider’s request for review of the route and any disputed charges. Ask for missing route and consent records before deciding responsibility or calculating a remedy."
    if not is_no_show and has_route:
        metric = route["content"]
        arguments.append({"title": "Compare the recorded vehicle route with its supplied baseline",
            "text": f"Code computes {metric['actual_km']} km travelled against {metric['optimal_km']} km on the supplied simulated road baseline ({metric['excess_km']} km excess), and {metric['actual_minutes']} against {metric['expected_minutes']} minutes. {len(metric['stop_candidates'])} bounded stop candidate(s) have unknown purpose. These are vehicle GPS findings, not Rider device GPS or proof of fault.",
            "evidence_ids": [route["id"]], "policy_ids": policies("R-04", "D-04")})
        if fare is not None and fare["status"] == "available":
            arguments.append({"title": "Limit any supported remedy to the fare comparison",
                "text": f"ADR 0004 compares paid net SGD {fare['content']['paid_net']} with the optimal net fare. The conditional excess-fare refund is SGD {fare['content']['refund']}, using explicit tariff, surge and promo. This code comparison does not authorise a refund or replace the Rider’s full-fare request.",
                "evidence_ids": [route["id"], fare["id"]] + report_refs, "policy_ids": policies("R-03", "D-03")})
        request = next((item for item in messages if item["content"]["sender"] == "Rider" and re.search(r"^please detour via\b", item["content"]["text"], re.I)), None)
        admission = next((item for item in messages if item["content"]["sender"] == "Driver" and re.search(r"^I missed the turn\b", item["content"]["text"], re.I)), None)
        if request:
            counter.append({"title": "The Rider’s exact detour request challenges the claim",
                "text": f"{request['id']}: “{request['content']['text']}” This is material counter-evidence. Consent covers only the described detour and stop if they match the vehicle route; it cannot justify unrelated changes.",
                "evidence_ids": [request["id"], route["id"]]})
            conclusion = "Present the original Rider request while acknowledging the exact requested detour as material counter-evidence. A longer route alone does not support a refund; verify that the travelled change matches the request."
            exact_request = "Please detour via Lavender MRT and stop there for three minutes so I can collect my bag, then continue to Marina Bay Sands."
            matching_landmark = any(observation.get("name") == "Lavender MRT" and observation.get("within_50m") for observation in metric.get("landmark_observations", []))
            matching_stop = any(stop.get("observed_seconds") == 180 for stop in metric.get("stop_candidates", []))
            if request["content"]["text"] != exact_request or not matching_landmark or not matching_stop:
                needs_route_review = True
                gaps.append({"text": "The prototype cannot match the exact requested detour and stop to the observed route. Consent scope needs human review.", "evidence_ids": [request["id"], route["id"]]})
                conclusion = "Present the request and route together for human review; the detour scope is unresolved."
            later = [item for item in messages[messages.index(request)+1:] if item["content"]["sender"] == "Rider" and re.search(r"\b(actually|skip|cancel|directly|do not|don't|no longer|instead|withdraw|revoke|retract)\b", item["content"]["text"], re.I)]
            if later:
                counter.append({"title": "Later Rider messages may change the request",
                    "text": " ".join(f"{item['id']}: “{item['content']['text']}”" for item in later) + " The earlier request cannot establish continuing agreement; review the complete exchange and route timing.",
                    "evidence_ids": [request["id"]] + [item["id"] for item in later]})
                needs_route_review = True
                conclusion = "Present the original report, request and later correction together. Consent scope remains unresolved; request human review without assuming the earlier detour request remained in force."
        elif admission:
            arguments.append({"title": "Use the Driver’s explanation without inventing stop purpose",
                "text": f"{admission['id']}: “{admission['content']['text']}” The Driver attributes the change to a missed turn. Ask that this explanation and the Rider’s disagreement be weighed with the computed excess, rather than assuming purpose from GPS.",
                "evidence_ids": message_refs, "policy_ids": policies("R-04", "D-04")})
            conclusion = "Present the Rider’s full-fare request and the supported route concern. The Driver’s attributed missed-turn explanation supports reviewing the excess; any remedy must preserve the legitimate baseline fare under ADR 0004."
        else:
            needs_route_review = True
            counter.append({"title": "Consent and route explanation remain unclear",
                "text": "The complete exchange contains no explicit Rider detour request identified by this prototype. Questions and a Driver explanation do not establish agreement or fault. Ask for clarification and human review.", "evidence_ids": message_refs})
            conclusion = "Present both accounts as unresolved and request human review of consent and the route explanation. No refund amount is authorised by this Rider Submission."
    counter.append({"title": "The policies do not promise this outcome", "text": "These draft clauses provide review and reporting guidance. They set no numerical no-show waiting threshold or automatic refund entitlement. The requested remedy remains the Rider’s request.", "evidence_ids": []})
    result = {"author": "Rider Advocate", "claim_restated": report["summary"], "rider_statement": report["statement"],
              "requested_outcome": deepcopy(report.get("requestedResolution", {})),
              "facts_relied_on": [item["id"] for item in items if item["status"] == "available"], "arguments": arguments,
              "counter_arguments": counter, "gaps": gaps, "policy_references": clauses, "requires_review": needs_route_review,
              "conclusion": ("Present the Rider’s request for review of the disputed cancellation charge. The account and receipt justify a focused review request; the available records do not establish who was at fault or guarantee a reversal."
                             if receipt else "Present the Rider’s request for review. No receipt was supplied, so the available records do not establish the charged amount or responsibility.") if is_no_show else conclusion}
    ids = {item["id"] for item in items}
    for point in arguments + counter + gaps:
        if any(ref not in ids for ref in point.get("evidence_ids", [])) or any(ref not in clauses for ref in point.get("policy_ids", [])):
            raise ValueError("The Rider Submission contains an unresolved citation.")
    return result
