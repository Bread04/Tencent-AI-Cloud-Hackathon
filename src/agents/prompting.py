"""What agents are allowed to put in a prompt."""

import json

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


def policy_for_prompt(case: Case) -> str:
    """The Policy Clauses applying to the Case, as JSON. Advocates and the Judge get the same text."""
    return json.dumps([clause.model_dump(mode="json") for clause in case.policy_clauses], indent=2)
