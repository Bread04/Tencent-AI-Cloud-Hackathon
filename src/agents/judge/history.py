"""The History step (architecture.md section 6.2, ADR 0001).

Runs in code after the Judge has fixed the outcome. A small published rule table
can lower Confidence or add a Review Trigger. It cannot raise Confidence and it
cannot change the outcome, the Remedy or the amount. Each rule that fires is
listed in the Ruling with its reason.
"""

from src.config import CONFIG, HistoryRule
from src.contracts import (
    Case,
    HistoryAdjustment,
    ReviewTrigger,
    ReviewTriggerRecord,
    Ruling,
    RulingStatus,
)

# PLACEHOLDER (contract-decisions open item 2): "several prior rejected disputes". The sample records the total
# rejected, not per category.
PRIOR_REJECTED_MIN = 3


def apply_history(ruling: Ruling, case: Case, rules: tuple[HistoryRule, ...] = CONFIG.history_rules) -> Ruling:
    history = next((item for item in case.evidence if item.source == "history"), None)
    if history is None or ruling.confidence is None:
        return ruling
    claimant = history.content[case.dispute.claimant.value]

    adjustments, triggers, cut = [], [], 0.0
    for rule in rules:
        reason = _reason_it_fires(rule.key, claimant)
        if reason is None:
            continue
        step = CONFIG.confidence.history_step if rule.lowers_confidence else 0
        cut += step
        adjustments.append(HistoryAdjustment(rule=rule.key, reason=reason, confidence_step=step))
        if rule.triggers_review:
            triggers.append(ReviewTriggerRecord(trigger=ReviewTrigger.HISTORY_RULE, reason=f"{rule.description}: {reason}"))
    if not adjustments:
        return ruling

    cut = min(cut, CONFIG.confidence.history_max)
    confidence = ruling.confidence.model_copy(update={"value": round(max(0.0, ruling.confidence.value - cut), 2)})
    return ruling.model_copy(
        deep=True,
        update={
            "confidence": confidence,
            "history_adjustments": [*ruling.history_adjustments, *adjustments],
            "review_triggers": [*ruling.review_triggers, *triggers],
            "status": RulingStatus.PROPOSAL if triggers else ruling.status,
        },
    )


def _reason_it_fires(key: str, claimant: dict) -> str | None:
    if key == "prior_rejected":
        rejected = claimant["dispute_history"]["rejected"]
        if rejected >= PRIOR_REJECTED_MIN:
            return f"The Claimant has {rejected} prior rejected disputes."
    if key == "late_cancel_flag":
        if "late_cancellations" in (claimant.get("fraud_flag_details") or ""):
            return "The Claimant is flagged for frequent late cancellations."
    return None
