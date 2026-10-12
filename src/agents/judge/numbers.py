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
    "route_comparison": "route",
    "fare_calculation": "fare",
    "route_conversation": "chat",
    "driver_at_pickup": "gps",
    "arrival_vs_scheduled": "gps",
    "wait_timers": "fare",
    "contact_attempts": "chat",
    "rider_position": "rider_location",
}


def amount_for(case: Case, remedy: Remedy, input_ids: list[str]) -> tuple[Decimal | None, Calculation | None]:
    """Recompute the amount from the validated sealed Evidence Items.

    Fee reversal uses the charged fee; route refunds use ADR 0004 receipt and tariff inputs.
    """
    if remedy in (Remedy.FULL_REFUND, Remedy.PARTIAL_REFUND):
        from src.tools.evidence.route import analyze_fare, ADR
        route = next(item for item in case.evidence if item.source == "route")
        fare = next(item for item in case.evidence if item.source == "fare")
        # Recompute from the sealed receipt and tariff; never trust a model amount.
        computed = analyze_fare(fare.content, route.derived)
        if not computed["available"]:
            raise ValueError(computed["unavailable_reason"])
        amount = Decimal(computed["refund"])
        values = {**computed["tariff"], "paid_net": computed["paid_net"], "optimal_km": route.derived["optimal_km"],
                  "expected_minutes": route.derived["expected_minutes"], "optimal_net": computed["optimal_net"]}
        formula = ("ADR 0004 (" + ADR + "): optimal_net=max(0,(base+optimal_km*km_rate+expected_minutes*minute_rate)*surge+booking+tolls-promo); "
                   "refund=min(paid_net,max(0,paid_net-optimal_net)); final SGD cents half-up; " + "; ".join(f"{key}={value}" for key, value in values.items()))
        return amount, Calculation(formula=formula, input_evidence_ids=list(input_ids), result=amount)
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
    case: Case, policy_fit: PolicyFit, checklist: list[MaterialEvidenceEntry], own_findings: list[OwnFinding]
) -> Confidence:
    """The lowest of its components: a Ruling is only as sound as its weakest support."""
    settings = CONFIG.confidence
    conflicting = any(item.status is EvidenceStatus.CONFLICTING for item in case.evidence)
    components = {
        "policy_fit": settings.policy_fit[policy_fit],
        "evidence_completeness": sum(entry.available for entry in checklist) / len(checklist),
        "consistency": settings.consistency_conflict if conflicting else settings.consistency_no_conflict,
    }
    if any(finding.decisive for finding in own_findings):
        components["own_finding_cap"] = settings.decisive_own_finding_cap  # a point neither advocate argued decided it
    return Confidence(value=min(components.values()), components=components)
