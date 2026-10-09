"""Configuration: Supporting Agent switches and the contract-session decisions.

Shared file (Braedon holds the pen). Code reads these values from `CONFIG`;
nothing else should hard-code them.

STATUS: every value here is PROPOSED, pending confirmation with Kyven.
The reasoning and the open questions are in docs/contract-decisions.md.
Keep the two files in step.
"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.contracts import DisputeCategory, PolicyFit, ReviewTrigger, Score, Switches


class _Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ConfidenceSettings(_Settings):
    """Confidence is the lowest of its components (architecture.md section 6.1)."""

    policy_fit: dict[PolicyFit, Score] = {
        PolicyFit.CLEAR: 0.95,
        PolicyFit.ARGUABLE: 0.75,
        PolicyFit.UNCLEAR: 0.5,
    }
    # Evidence completeness has no constant: it is the share of the category's
    # material-evidence checklist that is available.
    consistency_no_conflict: Score = 0.95
    consistency_conflict: Score = 0.65  # a conflict on a material item
    stability_agree: Score = 0.95  # Tier 1
    stability_disagree: Score = 0.5
    stability_margin: Score = 0.1  # PLACEHOLDER: Confidence gap between passes that counts as disagreement
    authenticity_failed_or_unknown: Score = 0.5  # Tier 3, a photo that matters
    decisive_own_finding_cap: Score = 0.75
    history_step: Score = 0.1  # per History rule that fires
    history_max: Score = 0.2  # most that History can lower Confidence


class EscalationSettings(_Settings):
    """When a Ruling goes to a Human Reviewer (architecture.md section 5.7)."""

    confidence_threshold: Score = 0.7  # below this, escalate
    amount_limit: Decimal = Decimal("50.00")  # PLACEHOLDER: a Ruling amount above this is reviewed
    triggers: tuple[ReviewTrigger, ...] = tuple(ReviewTrigger)  # any one escalates


class ModelSettings(_Settings):
    """How agents talk to the model (architecture.md sections 6.4 and 8)."""

    structured_output: Literal["json_schema"] = "json_schema"  # schema-constrained JSON, validated in code
    repair_attempts: int = Field(default=2, ge=0)  # retries with the validation error fed back


class HistoryRule(_Settings):
    """One row of the History rule table (architecture.md section 6.2).

    A rule can only lower Confidence (by `ConfidenceSettings.history_step`) or
    add a Review Trigger. There is deliberately no way to raise Confidence or
    change the outcome.
    """

    key: str
    description: str
    lowers_confidence: bool = True
    triggers_review: bool = False


class Config(_Settings):
    switches: Switches = Switches()  # every Supporting Agent off = Tier 0 MVP
    currency: str = "SGD"
    confidence: ConfidenceSettings = ConfidenceSettings()
    escalation: EscalationSettings = EscalationSettings()
    model: ModelSettings = ModelSettings()

    # Material evidence per Dispute Category: checklist key -> label shown in the Ruling.
    # Only No-Show Charge is defined so far; the rest arrive with their policy.
    material_evidence: dict[DisputeCategory, dict[str, str]] = {
        DisputeCategory.NO_SHOW_CHARGE: {
            "driver_at_pickup": "Driver position at the pickup point",
            "arrival_vs_scheduled": "Arrival time against the scheduled time",
            "wait_timers": "Free-wait and no-show timers",
            "contact_attempts": "Driver contact attempts",
            "rider_position": "Rider position",
        },
    }

    # PLACEHOLDER table, taken from the Judge prototype.
    history_rules: tuple[HistoryRule, ...] = (
        HistoryRule(
            key="prior_rejected",
            description="Claimant has 3 or more prior rejected disputes of this category",
        ),
        HistoryRule(
            key="late_cancel_flag",
            description="Claimant is flagged for frequent late cancellations",
        ),
    )


CONFIG = Config()
