"""What agents are allowed to put in a prompt."""

import json

from src.agents.policy.precedents import why_similar
from src.contracts import Case

# ADR 0001: History is withheld from the advocates and the Judge. It stays in the
# Case for the rule table that runs after the outcome is fixed.
WITHHELD_SOURCES = frozenset({"history"})


def evidence_for_prompt(case: Case) -> str:
    """The sealed evidence a model may see, as JSON."""
    items = [item.model_dump(mode="json") for item in case.evidence if item.source not in WITHHELD_SOURCES]
    for item in items:
        if item["source"] == "route":
            item["content"] = "Raw vehicle GPS and baseline geometry are retained in the sealed evidence; use the computed metrics and provenance below."
    return json.dumps(items, indent=2)


PRECEDENT_NOTE = (
    "Precedents (advisory: evidence and policy come first. A Judge cites one by ID in cited_precedent_ids only if it relied on it, "
    "and explains in precedent_departure why its Remedy differs from a precedent shown here)"
)


def precedents_for_prompt(case: Case) -> str | None:
    """The similar past Rulings served for this Case, or None when the precedent switch is off. Every agent gets the same text."""
    if not case.switches.policy_precedent:
        return None
    if not case.precedents:
        return f"{PRECEDENT_NOTE}:\nNo precedent found for this Case."
    shown = [
        {
            "precedent_id": p.precedent_id,
            "source": p.source.value,
            "similar_because": why_similar(case, p),
            "case_summary": p.case_summary,
            "outcome": p.ruling.outcome.value,
            "remedy": p.ruling.remedy.value,
            "policy_clauses_cited": p.ruling.cited_policy_clause_ids,
            "reasoning": p.ruling.reasoning_summary,
        }
        for p in case.precedents
    ]
    return f"{PRECEDENT_NOTE}:\n{json.dumps(shown, indent=2)}"


def policy_for_prompt(case: Case) -> str:
    """The Policy Clauses applying to the Case, as JSON. Advocates and the Judge get the same text."""
    return json.dumps([clause.model_dump(mode="json") for clause in case.policy_clauses], indent=2)
