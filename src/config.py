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
    stability_margin: Score = 0.1  # the Confidence gap between passes that counts as disagreement (confirmed 13 Oct 2026)
    authenticity_failed_or_unknown: Score = 0.5  # Tier 3, a photo that matters
    decisive_own_finding_cap: Score = 0.75
    history_step: Score = 0.05  # per History rule that fires (confirmed 13 Oct 2026; 0.1 pulled the DISP-002 demo case below the threshold)
    history_max: Score = 0.2  # most that History can lower Confidence


class EscalationSettings(_Settings):
    """When a Ruling goes to a Human Reviewer (architecture.md section 5.7)."""

    confidence_threshold: Score = 0.7  # below this, escalate
    amount_limit: Decimal = Decimal("50.00")  # a Ruling amount above this is reviewed (confirmed 13 Oct 2026)
    triggers: tuple[ReviewTrigger, ...] = tuple(ReviewTrigger)  # any one escalates


class PrecedentSettings(_Settings):
    """How Precedents are retrieved (architecture.md section 5.3, ADR 0003)."""

    retrieval: Literal["tags", "embeddings"] = "tags"  # embeddings reranks the tag candidates and falls back to tags
    limit: int = Field(default=3, ge=1)  # most Precedents served for one Case


class ModelSettings(_Settings):
    """How agents talk to the model (architecture.md sections 6.4 and 8)."""

    structured_output: Literal["json_schema", "json_object"] = "json_schema"  # JSON the reply must match, validated in code; json_object puts the schema in the prompt for providers without schema support
    repair_attempts: int = Field(default=2, ge=0)  # retries with the validation error fed back
    timeout_seconds: float = Field(default=120.0, gt=0)  # every model call; a timeout is a failure, not a hang. Reasoning models are slow
    rate_limit_retries: int = Field(default=6, ge=0)  # how often a call waits out a provider's rate limit before it fails


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
    switches: Switches = Switches(escalation=True)  # the other Supporting Agents off; Escalation on for the demo (ticket 09)
    currency: str = "SGD"
    confidence: ConfidenceSettings = ConfidenceSettings()
    escalation: EscalationSettings = EscalationSettings()
    precedents: PrecedentSettings = PrecedentSettings()
    model: ModelSettings = ModelSettings()

    # Material evidence per Dispute Category: checklist key -> label shown in the Ruling.
    # No-Show Charge and Route Deviation have defined policy and code rules.
    material_evidence: dict[DisputeCategory, dict[str, str]] = {
        DisputeCategory.ROUTE_DEVIATION: {
            "route_comparison": "Computed vehicle route and supplied road baseline",
            "fare_calculation": "Reconciled tariff and authoritative receipt",
            "route_conversation": "Route discussion and exact consent scope",
        },
        DisputeCategory.NO_SHOW_CHARGE: {
            "driver_at_pickup": "Driver position at the pickup point",
            "arrival_vs_scheduled": "Arrival time against the scheduled time",
            "wait_timers": "Free-wait and no-show timers",
            "contact_attempts": "Driver contact attempts",
            "rider_position": "Rider position",
        },
        DisputeCategory.SAFETY_INCIDENT: {
            "trip_route": "Route, speed and stops recorded for the trip",
            "conversation": "Messages between rider and driver",
        },
        DisputeCategory.PROPERTY_DAMAGE: {
            "damage_claim": "The cleaning fee claimed and who claims it",
            "damage_photos": "Photo findings: what they show, when taken, signs of AI generation",
            "conversation": "Messages between rider and driver",
            "trip_record": "The Trip the damage is said to have happened on",
        },
    }
    cleaning_fee_cap: Decimal = Decimal("50.00")  # PLACEHOLDER (ADR 0005): the most a cleaning fee can be, in SGD

    # The confirmed rule table (contract-decisions item 2, 13 Oct 2026).
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
