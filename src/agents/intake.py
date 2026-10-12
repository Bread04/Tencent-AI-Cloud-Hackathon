"""Intake: settle which kind of dispute this is (architecture.md section 5.1).

A chosen category is kept as it is. With none chosen, the description is classified by code into one, and a
description that fits none is rejected with a clear error. A safety-related word wins, so a safety report is
never filed as a fee dispute. A model could classify ambiguous text, but code is predictable and reviewable.
"""

import re
from dataclasses import dataclass

from src.agents.routing import SAFETY_WORDS
from src.contracts import DisputeCategory

# Checked in this order: the first category with a match wins.
RULES: list[tuple[DisputeCategory, re.Pattern]] = [
    (DisputeCategory.SAFETY_INCIDENT, SAFETY_WORDS),
    (DisputeCategory.PROPERTY_DAMAGE, re.compile(r"\b(stain\w*|scratch\w*|dent\w*|spill\w*|vomit\w*|damag\w*|broke\w*|torn|dirty)", re.IGNORECASE)),
    (DisputeCategory.ROUTE_DEVIATION, re.compile(r"\b(route|detour\w*|longer|wrong way|different way|took a different|off the map)", re.IGNORECASE)),
    (DisputeCategory.NO_SHOW_CHARGE, re.compile(r"(no[- ]show|cancel\w*|did(n't| not) show|waited|waiting|cancellation fee)", re.IGNORECASE)),
]


class IntakeError(ValueError):
    """The Dispute cannot be filed, with the reason in words for the person who filed it."""


@dataclass(frozen=True)
class Classification:
    category: DisputeCategory
    matched: list[str]


def classify(description: str) -> Classification:
    for category, pattern in RULES:
        found = sorted({match.group(0).lower() for match in pattern.finditer(description)})
        if found:
            return Classification(category, found)
    raise IntakeError("We could not tell which kind of dispute this is. Say what went wrong, for example a charge, the route, damage or safety.")


def resolve_category(chosen: str | None, description: str) -> DisputeCategory:
    if chosen:
        try:
            return DisputeCategory(chosen)
        except ValueError:
            raise IntakeError(f"'{chosen}' is not a dispute category.") from None
    return classify(description).category
