"""Everything numeric in a Ruling is computed here by code, never by the model: the amount and Confidence."""

from decimal import Decimal

from src.config import CONFIG
from src.contracts import (
    Calculation,
    Case,
    Confidence,
    EvidenceStatus,
    MaterialEvidenceEntry,
    OwnFinding,
    PolicyFit,
    Remedy,
)

# Which evidence source answers each line of the material-evidence checklist.
CHECKLIST_SOURCES = {
    "driver_at_pickup": "gps",
    "arrival_vs_scheduled": "gps",
    "wait_timers": "fare",
    "contact_attempts": "chat",
    "rider_position": "rider_location",
}


def amount_for(case: Case, remedy: Remedy, input_ids: list[str]) -> tuple[Decimal | None, Calculation | None]:
    """Recompute the amount from the Evidence Items the Judge named (already checked to be fare items).

    Of the Remedies, only a fee reversal has its amount computed so far; the others carry no amount.
    """
    if remedy is not Remedy.FEE_REVERSAL:
        return None, None
    fare = next(item for item in case.evidence if item.evidence_id == input_ids[0])
    fee = Decimal(fare.derived["cancellation_fee"])
    return fee, Calculation(formula="no-show fee charged, reversed in full", input_evidence_ids=list(input_ids), result=fee)


def checklist_for(case: Case) -> list[MaterialEvidenceEntry]:
    labels = CONFIG.material_evidence[case.dispute.category]
    return [
        MaterialEvidenceEntry(
            key=key,
            label=label,
            evidence_ids=[
                item.evidence_id
                for item in case.evidence
                if item.source == CHECKLIST_SOURCES[key] and item.status is not EvidenceStatus.MISSING
            ],
        )
        for key, label in labels.items()
    ]


def confidence_for(
    case: Case,
    policy_fit: PolicyFit,
    checklist: list[MaterialEvidenceEntry],
    own_findings: list[OwnFinding],
    stable: bool | None = None,
) -> Confidence:
    """The lowest of its components: a Ruling is only as sound as its weakest support."""
    settings = CONFIG.confidence
    conflicting = any(item.status is EvidenceStatus.CONFLICTING for item in case.evidence)
    components = {
        "policy_fit": settings.policy_fit[policy_fit],
        "evidence_completeness": sum(entry.available for entry in checklist) / len(checklist),
        "consistency": settings.consistency_conflict if conflicting else settings.consistency_no_conflict,
    }
    if stable is not None:  # only when the stability check ran: agreement is no cap, disagreement caps Confidence
        components["stability"] = settings.stability_agree if stable else settings.stability_disagree
    if any(finding.decisive for finding in own_findings):
        components["own_finding_cap"] = settings.decisive_own_finding_cap  # a point neither advocate argued decided it
    return Confidence(value=min(components.values()), components=components)
