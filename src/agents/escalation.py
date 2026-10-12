"""The Escalation Protocol (architecture.md section 5.7): code decides whether a Ruling may be finalized.

A Ruling that should not be finalized automatically stays a proposal for a Human Reviewer, with the reason
recorded as a Review Trigger. Escalation sits behind a switch: with it off every Ruling is finalized, as in
Tier 0. The review package, the queue and the reviewer's decision are further down this module.
"""

from src.contracts import ReviewTrigger, ReviewTriggerRecord, Ruling, RulingStatus


def apply_escalation(ruling: Ruling, *, enabled: bool, threshold: float) -> Ruling:
    """Hold a Ruling for review when its Confidence is below `threshold`; finalize everything when escalation is off.

    Run after the History step, so a Ruling that History pulls below the threshold is held too.
    Other triggers (balanced evidence, a Policy Gap, a History rule) are added where they arise and already
    leave the Ruling a proposal; this adds the Confidence one and does not repeat it.
    """
    if not enabled:
        return ruling.model_copy(update={"status": RulingStatus.FINAL})
    triggers = list(ruling.review_triggers)
    below = ruling.confidence is not None and ruling.confidence.value < threshold
    if below and ReviewTrigger.LOW_CONFIDENCE not in [record.trigger for record in triggers]:
        triggers.append(
            ReviewTriggerRecord(
                trigger=ReviewTrigger.LOW_CONFIDENCE,
                reason=f"Calculated confidence {ruling.confidence.value} is below the configured threshold {threshold}.",
            )
        )
    return ruling.model_copy(update={"status": RulingStatus.PROPOSAL if triggers else ruling.status, "review_triggers": triggers})
