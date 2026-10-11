"""What agents are allowed to put in a prompt."""

import json

from src.contracts import Case

# ADR 0001: History is withheld from the advocates and the Judge. It stays in the
# Case for the rule table that runs after the outcome is fixed.
WITHHELD_SOURCES = frozenset({"history"})


def evidence_for_prompt(case: Case) -> str:
    """The sealed evidence a model may see, as JSON."""
    items = [item.model_dump(mode="json") for item in case.evidence if item.source not in WITHHELD_SOURCES]
    return json.dumps(items, indent=2)
