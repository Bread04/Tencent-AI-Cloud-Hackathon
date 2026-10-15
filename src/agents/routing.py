"""The SLA & Routing Manager (architecture.md section 5.1): a Priority and a reason for every Case.

Priority is a scoring function over category, urgency (safety-related words in the description) and the
disputed value. Higher is more urgent, so the review queue orders by descending priority. The scale is the
confirmed one (contract-decisions item 9): category points (Safety 100 > Property 40 > Route 30 > No-Show 20),
plus urgency and a little for the amount. A Safety Incident always outranks every other category, however small its fee.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from src.contracts import Dispute, DisputeCategory

CATEGORY_POINTS = {
    DisputeCategory.SAFETY_INCIDENT: 100,
    DisputeCategory.PROPERTY_DAMAGE: 40,
    DisputeCategory.ROUTE_DEVIATION: 30,
    DisputeCategory.NO_SHOW_CHARGE: 20,
}
SAFETY_WORDS = re.compile(
    r"\b(unsafe|danger\w*|accident|crash\w*|injur\w*|assault\w*|harass\w*|threat\w*|abus\w*|red light|speeding|sped|too fast|reckless\w*|emergency|violen\w*)",
    re.IGNORECASE,
)
URGENCY_POINTS = 30  # a safety-related word in any category
VALUE_STEP = Decimal("10")  # one point per this much of the disputed amount
VALUE_CAP = 10


@dataclass(frozen=True)
class Priority:
    value: int
    reason: str


def score(dispute: Dispute, amount: Decimal) -> Priority:
    """The Priority of a Dispute: category points, plus urgency if it uses safety words, plus a little for the amount."""
    category = dispute.category
    points = CATEGORY_POINTS[category]
    parts = [f"{category.value.replace('_', ' ')} (+{points})"]
    words = sorted({match.group(0).lower() for match in SAFETY_WORDS.finditer(dispute.description)})
    if words:
        points += URGENCY_POINTS
        parts.append(f"safety-related words: {', '.join(words)} (+{URGENCY_POINTS})")
    value_points = min(int(amount // VALUE_STEP), VALUE_CAP)
    if value_points:
        points += value_points
        parts.append(f"amount {amount} (+{value_points})")
    return Priority(points, "; ".join(parts))
