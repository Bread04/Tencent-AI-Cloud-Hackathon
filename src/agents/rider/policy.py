"""Deterministic Rider policy retrieval from the shared synchronized JSON."""

import re

from .catalog import load_policy
from .validation import validate_report

CATEGORY_REFS = {
    "No-show / cancellation": ["R-02"], "Route deviation": ["R-04", "D-04", "R-03", "D-03"],
    "Fare / payment": ["R-03"], "Safety / conduct": ["R-05"], "Damage / mess": ["R-07"],
    "Lost item": ["R-08"], "Other": ["R-09"],
}


def retrieve(report, limit=None):
    validate_report(report, confirmed=False)
    policies = load_policy()
    text = " ".join(value for value in [report.get("category"), report.get("summary"), report.get("statement"),
        *report.get("categoryDetails", {}).values(), report.get("incident", {}).get("location"),
        *(item.get("caption") for item in report.get("evidence", []))] if isinstance(value, str)).lower()
    reasons = {}

    def add(clause_id, reason):
        if reason not in reasons.setdefault(clause_id, []):
            reasons[clause_id].append(reason)

    for clause_id in CATEGORY_REFS.get(report.get("category"), ["R-09"]):
        add(clause_id, f"Issue category: {report.get('category') or 'not provided'}")
    for clause in policies["clauses"]:
        if clause["role"] == "Rider":
            for keyword in clause["keywords"]:
                if len(keyword) > 2 and re.search(r"\b" + re.escape(keyword) + r"\b", text, re.I):
                    add(clause["clause_id"], f"Report wording relates to “{keyword}”")
    add("R-06", "General report-handling guidance")
    by_id = {clause["clause_id"]: clause for clause in policies["clauses"]}
    matches = [{"reference": key, "title": by_id[key]["title"], "category": by_id[key]["category"],
                "excerpt": by_id[key]["text"], "relevance_signals": reasons[key]}
               for key in sorted(reasons, key=lambda key: (-len(reasons[key]), key))]
    if report.get("category") != "Route deviation" and limit is not None:
        matches = matches[:limit]
    return {"schema_version": "prototype-1", "agent": "Rider Policy Agent", "policy_version": policies["version"],
            "status": "matched", "scope": "Rider report only; deterministic category and keyword matching.", "matches": matches,
            "limitations": ["References are informational draft guidance, not approved contract terms or legal advice.",
                "A match does not verify a reported event, determine responsibility, or recommend a refund, compensation, or other outcome.",
                "The local Python service reads the shared policy JSON; no model or live Ryde connection."]}


def preview(report):
    return retrieve(report, limit=5)
