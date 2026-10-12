"""Python-backed local Rider workflow 3 → 4 → 5; no model calls or payment actions."""

from copy import deepcopy
import re

from . import advocate, evidence, policy
from .catalog import RiderCatalog, load_policy
from .validation import validate_report, validate_scope

SUPPORTED = ("No-show / cancellation", "Route deviation")


def resolve_rider(report, selected_rider=None, *, catalog=None):
    validate_report(report)
    catalog = catalog or RiderCatalog()
    if selected_rider is not None:
        validate_scope(selected_rider, report["trip"]["reference"])
        catalog.trip(selected_rider, report["trip"]["reference"])
        return selected_rider
    owners = [rider["id"] for rider in catalog.riders() if any(trip["id"] == report["trip"]["reference"] for trip in catalog.trips(rider["id"]))]
    if len(owners) != 1:
        raise ValueError("This trip is not in the simulated Rider app. Your report can still be downloaded; no trip records were invented.")
    return owners[0]


def run(*, report, rider_id=None, catalog=None):
    catalog = catalog or RiderCatalog()
    owner = resolve_rider(report, rider_id, catalog=catalog)
    source = deepcopy(report)
    context = {"rider_id": owner, "trip_id": source["trip"]["reference"], "report_id": source["id"]}
    log = []
    def event(agent, kind, summary, references=None):
        log.append({"timestamp": evidence.timestamp(), "agent": agent, "kind": kind, "summary": summary, "references": references or []})
    event("Application", "intake_validated", "Confirmed the demo Rider, Trip, and report snapshot.")
    if source["category"] not in SUPPORTED:
        event("Application", "support_routing_required", "This category is outside the two configured case-building categories. No Advocate Submission was generated.")
        return {"schema_version": "local-rider-case-1", "status": "support_required", "context": context, "original_report": source,
                "communication_log": log, "message": "This prototype prepares Rider cases for no-show/cancellation and route deviation. This report needs a support or safety review. Nothing has been sent to a reviewer; keep the report JSON.", "simulated": True}
    event("Application", "agent_dispatched", "Step 3 · Ask the Rider Evidence Agent to gather this report’s trip records.")
    snapshot = evidence.collect(rider_id=owner, trip_id=context["trip_id"], report=source, catalog=catalog)
    for entry in snapshot["log"]:
        event(entry["agent"], "evidence_requested" if entry["kind"] == "evidence_request" else "evidence_returned", entry["summary"], entry.get("references"))
    event("Application", "handoff_recorded", "Evidence Agent → local case store → Policy Agent: original report, source IDs, and missing-data flags.", [item["id"] for item in snapshot["items"]])
    event("Application", "agent_dispatched", "Step 4 · Ask the Rider Policy Agent for relevant clauses from the shared draft policy version.")
    retrieved = policy.retrieve(source)
    policies = load_policy()
    if retrieved["policy_version"] != policies["version"] or retrieved["status"] != "matched":
        raise ValueError("The policy output does not match the case policy source.")
    for match in retrieved["matches"]:
        clause = next((clause for clause in policies["clauses"] if clause["clause_id"] == match["reference"] and (clause["role"] == "Rider" or (source["category"] == "Route deviation" and clause["clause_id"] in ("D-04", "D-03")))), None)
        if clause is None or clause["text"] != match["excerpt"]:
            raise ValueError("Policy source verification failed.")
    event("Rider Policy Agent", "policy_retrieved", f"Retrieved {len(retrieved['matches'])} clauses from {retrieved['policy_version']}. Matches are guidance, not findings.", [match["reference"] for match in retrieved["matches"]])
    event("Application", "rider_snapshot_frozen", "Preserved an immutable Rider-visible evidence snapshot. A complete shared Case evidence set and Judge review are not implemented.")
    event("Application", "handoff_recorded", "Evidence + Policy → local case store → Rider Advocate: complete outputs, report, gaps, and policy limits.")
    submission = advocate.prepare(report=source, evidence=snapshot, policy=retrieved)
    safety_review = bool(re.search("unsafe|threat|harass|danger|violence|assault|weapon|injur|crash", " ".join([source["summary"], source["statement"], *source.get("categoryDetails", {}).values()]), re.I))
    review_required = safety_review or submission["requires_review"]
    reasons = []
    if safety_review:
        reasons.append("Possible safety concern: human review is needed. This demo has not contacted support or emergency services.")
    if submission["requires_review"]:
        reasons.append("Route evidence, pricing or consent needs human review. This Rider Submission authorises no refund and has not been sent to support.")
    event("Rider Advocate", "submission_prepared", "Step 5 · Prepared the Rider’s strongest supported review request, including counter-evidence and missing information.", submission["facts_relied_on"])
    if review_required:
        event("Application", "review_signal", " ".join(reasons))
    return deepcopy({"schema_version": "local-rider-case-1", "id": f"LOCAL-{source['id']}", "status": "draft", "context": context, "simulated": True,
        "original_report": source, "policy_version": retrieved["policy_version"], "rider_snapshot_version": f"{source['id']}:rider-snapshot:1",
        "evidence": snapshot, "policy": retrieved, "submission": submission, "review_required": review_required, "review_reasons": reasons, "communication_log": log,
        "limitations": ["Deterministic local Python prototype; no language model or live Ryde connection.", "Rider-visible evidence subset only; no Driver Submission, Judge Ruling, or payment action.", "Draft policies and reported claims do not establish entitlement. Media content is unavailable to these agents."]})
