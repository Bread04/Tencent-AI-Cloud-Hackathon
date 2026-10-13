"""Everything numeric in a Ruling is computed here by code, never by the model: the amount and Confidence."""

from decimal import ROUND_HALF_UP, Decimal

from src.config import CONFIG
from src.contracts import (
    Calculation,
    Case,
    Confidence,
    DisputeCategory,
    EvidenceSource,
    EvidenceStatus,
    MaterialEvidenceEntry,
    OwnFinding,
    PolicyFit,
    Remedy,
    RulingOutcome,
)

# Which evidence source answers each line of the material-evidence checklist. The keys must stay in step with
# `CONFIG.material_evidence` (src/config.py); a test asserts the two agree. Typed against the closed EvidenceSource
# so a misspelled source fails loudly instead of silently producing an empty checklist line.
CHECKLIST_SOURCES: dict[str, EvidenceSource] = {
    "route_comparison": EvidenceSource.ROUTE,
    "fare_calculation": EvidenceSource.FARE,
    "route_conversation": EvidenceSource.CHAT,
    "driver_at_pickup": EvidenceSource.GPS,
    "arrival_vs_scheduled": EvidenceSource.GPS,
    "wait_timers": EvidenceSource.FARE,
    "contact_attempts": EvidenceSource.CHAT,
    "rider_position": EvidenceSource.RIDER_LOCATION,
    "trip_route": EvidenceSource.GPS,
    "conversation": EvidenceSource.CHAT,
    "damage_claim": EvidenceSource.DAMAGE_CLAIM,
    "damage_photos": EvidenceSource.PHOTO_FINDING,
    "trip_record": EvidenceSource.TRIP,
}


def amount_for(case: Case, remedy: Remedy, input_ids: list[str], outcome: RulingOutcome | None = None) -> tuple[Decimal | None, Calculation | None]:
    """Recompute the amount from the validated sealed Evidence Items.

    Fee reversal uses the charged fee; route refunds use ADR 0004 receipt and tariff inputs.
    """
    if case.dispute.category is DisputeCategory.ROUTE_DEVIATION and remedy in (Remedy.FULL_REFUND, Remedy.PARTIAL_REFUND):
        from src.tools.evidence.route import analyze_route, analyze_fare, ADR
        route = next(item for item in case.evidence if item.source == "route")
        fare = next(item for item in case.evidence if item.source == "fare")
        # Recompute from the sealed receipt and tariff; never trust a model amount.
        metrics = analyze_route(route.content)
        computed = analyze_fare(fare.content, metrics)
        if not computed["available"]:
            raise ValueError(computed["unavailable_reason"])
        amount = Decimal(computed["refund"])
        values = {**computed["tariff"], "paid_net": computed["paid_net"], "optimal_km": metrics["optimal_km"],
                  "expected_minutes": metrics["expected_minutes"], "optimal_net": computed["optimal_net"]}
        formula = ("ADR 0004 (" + ADR + "): optimal_net=max(0,(base+optimal_km*km_rate+expected_minutes*minute_rate)*surge+booking+tolls-promo); "
                   "refund=min(paid_net,max(0,paid_net-optimal_net)); final SGD cents half-up; " + "; ".join(f"{key}={value}" for key, value in values.items()))
        return amount, Calculation(formula=formula, input_evidence_ids=list(input_ids), result=amount)
    if case.dispute.category is DisputeCategory.PROPERTY_DAMAGE:
        if remedy is not Remedy.COMPENSATION_TO_DRIVER:
            return None, None
        claim = next(item for item in case.evidence if item.evidence_id == input_ids[0])
        claimed = Decimal(claim.derived["claimed_fee"])
        fee = cleaning_fee(claimed, outcome or RulingOutcome.UPHOLD)
        formula = (f"ADR 0005: cleaning fee = min(claimed {claimed}, cap {CONFIG.cleaning_fee_cap})"
                   + ("; halved for a partial ruling, final SGD cents half-up" if outcome is RulingOutcome.PARTIALLY_UPHOLD else ""))
        return fee, Calculation(formula=formula, input_evidence_ids=list(input_ids), result=fee)
    if remedy is not Remedy.FEE_REVERSAL:
        return None, None
    fare = next(item for item in case.evidence if item.evidence_id == input_ids[0])
    fee = Decimal(fare.derived["cancellation_fee"])
    return fee, Calculation(formula="no-show fee charged, reversed in full", input_evidence_ids=list(input_ids), result=fee)


def cleaning_fee(claimed: Decimal, outcome: RulingOutcome) -> Decimal | None:
    """The cleaning fee the rider pays (ADR 0005): the claimed fee up to the cap; half of that for a partial ruling; nothing if rejected."""
    if outcome is RulingOutcome.REJECT:
        return None
    full = min(claimed, CONFIG.cleaning_fee_cap)
    return (full / 2 if outcome is RulingOutcome.PARTIALLY_UPHOLD else full).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def failed_authenticity_ids(case: Case) -> set[str]:
    """Photo findings that fail or leave unknown the Authenticity Check: a capture time outside the Trip or unknown, an AI-generation signal, or a photo not analysed."""
    failed = set()
    for item in case.evidence:
        if item.source != "photo_finding":
            continue
        if item.status is EvidenceStatus.MISSING:
            failed.add(item.evidence_id)
        elif item.evidence_id.endswith("-TIME") and item.derived.get("alignment") != "aligned":
            failed.add(item.evidence_id)
        elif item.evidence_id.endswith("-AI") and item.derived.get("signal") != "none":
            failed.add(item.evidence_id)
    return failed


def authenticity_problems(case: Case) -> list[str]:
    """One sentence per failed or unknown check, for the Review Trigger. Only Property Damage rests on photos."""
    if case.dispute.category is not DisputeCategory.PROPERTY_DAMAGE:
        return []
    by_id = {item.evidence_id: item for item in case.evidence}
    return [f"{evidence_id}: {by_id[evidence_id].content}" for evidence_id in sorted(failed_authenticity_ids(case))]


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
    if authenticity_problems(case):  # a failed or unknown Authenticity Check caps Confidence; it never decides the Case alone
        components["authenticity"] = settings.authenticity_failed_or_unknown
    if stable is not None:  # only when the stability check ran: agreement is no cap, disagreement caps Confidence
        components["stability"] = settings.stability_agree if stable else settings.stability_disagree
    if any(finding.decisive for finding in own_findings):
        components["own_finding_cap"] = settings.decisive_own_finding_cap  # a point neither advocate argued decided it
    return Confidence(value=min(components.values()), components=components)
