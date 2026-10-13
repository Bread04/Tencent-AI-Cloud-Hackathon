"""Precedent retrieval (architecture.md section 5.3, ADR 0003).

Precedents are filtered by the Case's category, ranked by tag overlap, and optionally reranked by an
embedding model. If the model is missing or fails, retrieval falls back to tags and says so. Only seeded
and human-reviewed Precedents are eligible: an unreviewed model Ruling can never become authority.

The Case's tags come from the sealed evidence, and never from History (ADR 0001), so retrieval cannot
bring History back to the Judge. A Precedent stores no party ID, trip ID or History-derived fact.
"""

import json
import math
import re
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Literal, Protocol

from src.config import CONFIG
from src.contracts import (
    BalanceOfEvidence,
    Calculation,
    Case,
    Confidence,
    DisputeCategory,
    EvidenceItem,
    EvidenceStatus,
    PolicyFit,
    Precedent,
    PrecedentSource,
    Remedy,
    Ruling,
    RulingOutcome,
    RulingStatus,
    Contract,
)

SEED_FILE = Path(__file__).resolve().parents[3] / "data" / "precedents" / "seed.json"
RETRIEVABLE = frozenset({PrecedentSource.SEEDED, PrecedentSource.HUMAN_CONFIRMED, PrecedentSource.HUMAN_OVERRIDE})
NO_PRECEDENT = "No precedent found for this Case."
NEAR_PICKUP_M = 50  # the driver counts as at the pickup point within this distance on arrival
FAR_ABOVE_LIMIT_KMH = 80  # a recorded speed at or above this is far above any road limit in the mock data
COMPLAINT = re.compile(r"slow down|unsafe|dangerous|scared|too fast|reckless|stop the car", re.IGNORECASE)
# A rider asking to change the route, and a driver agreeing to it. Deliberately positive (a rider's "I did not
# request this detour" is a denial, not a request); a driver-initiated suggestion is not agreement either.
DETOUR_REQUEST = re.compile(r"\bplease\b|detour via|go via|stop (at|there|for)|take (a|that) detour|drop (me|off)", re.IGNORECASE)
DETOUR_AGREE = re.compile(r"\byes\b|\bok(ay)?\b|\bsure\b|can (do|take)|go ahead|no problem", re.IGNORECASE)


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class ServedPrecedent(Contract):
    """A Precedent shown to the agents, with why it was chosen."""

    precedent: Precedent
    shared_tags: list[str]
    why: str


class Retrieval(Contract):
    served: list[ServedPrecedent]
    mode_requested: Literal["tags", "embeddings"]
    mode_used: Literal["tags", "embeddings"]
    note: str | None = None  # a fallback, or "No precedent found"


# --- The store ----------------------------------------------------------------------------------------------------------------


def seeded_precedents(path: Path = SEED_FILE) -> list[Precedent]:
    return [_precedent(spec) for spec in json.loads(path.read_text(encoding="utf-8"))["precedents"]]


def eligible(precedents: Sequence[Precedent]) -> list[Precedent]:
    """Seeded and human-reviewed Precedents only."""
    return [p for p in precedents if p.source in RETRIEVABLE]


def _precedent(spec: dict) -> Precedent:
    category = DisputeCategory(spec["category"])
    outcome, remedy = RulingOutcome(spec["outcome"]), Remedy(spec["remedy"])
    amount = Decimal("5.00") if remedy is Remedy.FEE_REVERSAL else Decimal("4.20") if remedy is Remedy.PARTIAL_REFUND else None
    ruling = Ruling(
        status=RulingStatus.FINAL,
        outcome=outcome,
        balance_of_evidence=BalanceOfEvidence.CLAIMANT if outcome is not RulingOutcome.REJECT else BalanceOfEvidence.RESPONDENT,
        remedy=remedy,
        amount=amount,
        currency=CONFIG.currency if amount is not None else None,
        calculation=Calculation(formula="amount of the original charge", input_evidence_ids=["EV-FARE-1"], result=amount) if amount is not None else None,
        policy_fit=PolicyFit.CLEAR,
        policy_fit_reason="The recorded facts matched the clauses cited.",
        cited_policy_clause_ids=spec["clauses"],
        reasoning_summary=spec["reasoning"],
        confidence=Confidence(value=0.9, components={"policy_fit": 0.95, "evidence_completeness": 0.9, "consistency": 0.95}),
    )
    return Precedent(
        precedent_id=spec["precedent_id"],
        case_summary=spec["case_summary"],
        ruling=ruling,
        source=PrecedentSource.SEEDED,
        category=category,
        similarity_tags=spec["tags"],
    )


# --- Tags from the Case ---------------------------------------------------------------------------------------------------------


def case_tags(case: Case) -> set[str]:
    """Describe the Case from its sealed evidence, in the vocabulary the Precedents of its category use. History is never read."""
    evidence = {item.source: item for item in case.evidence if item.source != "history"}  # ADR 0001: retrieval cannot bring History back
    if case.dispute.category is DisputeCategory.SAFETY_INCIDENT:
        return _safety_tags(evidence)
    if case.dispute.category is DisputeCategory.NO_SHOW_CHARGE:
        return _no_show_tags(case, evidence)
    if case.dispute.category is DisputeCategory.ROUTE_DEVIATION:
        return _route_tags(evidence)
    if case.dispute.category is DisputeCategory.PROPERTY_DAMAGE:
        return _property_tags(case.evidence)
    return set()


def _no_show_tags(case: Case, by_source: dict) -> set[str]:
    tags: set[str] = set()
    gps, chat, fare = (by_source.get(name) for name in ("gps", "chat", "fare"))
    if gps and gps.status is not EvidenceStatus.MISSING:
        near = gps.derived.get("distance_to_pickup_at_arrival_m")
        if near is not None:
            tags.add("driver_at_pickup" if near <= NEAR_PICKUP_M else "driver_away_from_pickup")
        early = gps.derived.get("arrival_vs_scheduled_min")
        if early is not None and early <= 0:
            tags.add("driver_on_time")
    if fare and fare.status is not EvidenceStatus.MISSING:
        if "free_wait_expired" in fare.derived:
            tags.add("free_wait_over" if fare.derived["free_wait_expired"] else "free_wait_not_over")
        if "no_show_threshold_reached" in fare.derived:
            tags.add("no_show_threshold_reached" if fare.derived["no_show_threshold_reached"] else "no_show_threshold_not_reached")
    if chat and chat.status is not EvidenceStatus.MISSING:
        contacted = chat.derived.get("driver_messages", 0) + chat.derived.get("driver_calls", 0)
        tags.add("driver_contacted_rider" if contacted else "driver_made_no_contact")
        if chat.derived.get("rider_messages", 0):
            tags.add("rider_replied")
    if any(item.source == "rider_location" and item.status is EvidenceStatus.MISSING for item in case.evidence):
        tags.add("rider_location_missing")
    return tags


def _safety_tags(by_source: dict) -> set[str]:
    """What the trip record shows about speed, the app's own alerts, the rider's complaints and how the trip ended."""
    tags: set[str] = set()
    gps, chat, fare = (by_source.get(name) for name in ("gps", "chat", "fare"))
    if gps and gps.status is not EvidenceStatus.MISSING and isinstance(gps.content, list):
        fastest = max((point.get("speed_kmh", 0) for point in gps.content), default=0)
        tags.add("speed_far_above_limit" if fastest >= FAR_ABOVE_LIMIT_KMH else "speed_near_limit")
    if fare and fare.status is not EvidenceStatus.MISSING and isinstance(fare.content, list):
        events = {event.get("event_type") for event in fare.content}
        tags.add("speed_alert_raised" if "speed_alert" in events else "no_alert_raised")
        tags.add("rider_ended_trip_early" if "trip_ended_early" in events else "trip_completed")
    if chat and chat.status is not EvidenceStatus.MISSING and isinstance(chat.content, list):
        complained = any(m.get("sender") == "rider" and COMPLAINT.search(m.get("content", "")) for m in chat.content)
        tags.add("rider_complained_in_chat" if complained else "no_complaint_in_chat")
    return tags


def _route_tags(by_source: dict) -> set[str]:
    """Describe a Route Deviation Case from the route geometry and the conversation: was it longer, and was a change agreed?"""
    tags: set[str] = set()
    route = by_source.get("route")
    if route and route.status is not EvidenceStatus.MISSING:
        excess = route.derived.get("excess_km")
        if excess is not None:
            tags.add("route_longer_than_expected" if Decimal(excess) > 0 else "route_not_longer_than_expected")
    chat = by_source.get("chat")
    if chat and chat.status is not EvidenceStatus.MISSING and isinstance(chat.content, list):
        requested = any(m.get("sender") == "rider" and DETOUR_REQUEST.search(m.get("content", "")) for m in chat.content)
        agreed = any(m.get("sender") == "driver" and DETOUR_AGREE.search(m.get("content", "")) for m in chat.content)
        tags.add("agreed_detour" if (requested and agreed) else "no_agreed_detour")
    return tags


def _property_tags(items: Sequence[EvidenceItem]) -> set[str]:
    """Describe a Property Damage Case from the claim and the photo findings (a photo's time and AI signal, never the image itself)."""
    tags: set[str] = set()
    for item in items:
        if item.status is EvidenceStatus.MISSING:
            continue
        if item.source == "damage_claim":
            tags.add("cleaning_fee_claimed")
        elif item.source == "photo_finding":
            if item.evidence_id.endswith("-TIME"):
                tags.add({"aligned": "photo_aligned", "outside_window": "photo_outside_window"}.get(item.derived.get("alignment"), "photo_time_unknown"))
            elif item.evidence_id.endswith("-AI"):
                tags.add("photo_ai_signal" if item.derived.get("signal") != "none" else "photo_no_ai_signal")
    return tags


# --- Retrieval ----------------------------------------------------------------------------------------------------------------------


def retrieve_precedents(
    case: Case,
    precedents: Sequence[Precedent],
    *,
    mode: Literal["tags", "embeddings"] = "tags",
    embedder: Embedder | None = None,
    query_text: str | None = None,
    limit: int | None = None,
) -> Retrieval:
    """Filter by category, rank by tag overlap, then (optionally) rerank by embedding similarity."""
    limit = limit or CONFIG.precedents.limit
    wanted = case_tags(case)
    candidates = []
    for precedent in eligible(precedents):
        shared = sorted(wanted & set(precedent.similarity_tags))
        if precedent.category is case.dispute.category and shared:
            candidates.append((precedent, shared))
    candidates.sort(key=lambda pair: (-len(pair[1]), pair[0].precedent_id))  # most shared tags first, then by id

    mode_used, note = "tags", None
    if mode == "embeddings":
        reranked, note = _rerank(candidates, query_text or _summary_of(case, wanted), embedder)
        if reranked is not None:
            candidates, mode_used = reranked, "embeddings"
    served = [ServedPrecedent(precedent=p, shared_tags=shared, why=_why(shared, mode_used)) for p, shared in candidates[:limit]]
    if not served:
        note = f"{NO_PRECEDENT} {note}" if note else NO_PRECEDENT
    return Retrieval(served=served, mode_requested=mode, mode_used=mode_used, note=note)


def why_similar(case: Case, precedent: Precedent) -> str:
    """Why this Precedent resembles this Case: the same category and the tags they share."""
    return _why(sorted(case_tags(case) & set(precedent.similarity_tags)), "tags")


def describe(retrieval: "Retrieval") -> str:
    """One line for the Communication Log: how many, by what method, from which sources, and any fallback."""
    if not retrieval.served:
        return retrieval.note or NO_PRECEDENT
    named = ", ".join(f"{s.precedent.precedent_id} ({s.precedent.source.value})" for s in retrieval.served)
    fell_back = f" {retrieval.note}" if retrieval.note else ""
    return f"{len(retrieval.served)} similar precedent(s) retrieved by {retrieval.mode_used}: {named}.{fell_back}"


def load_embedder() -> "Embedder | None":
    """The local open-source embedding model (ADR 0003: fastembed with a small BGE model), or None when it is not installed."""
    try:
        from fastembed import TextEmbedding
    except ImportError:
        return None
    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    class _Local:
        def embed(self, texts: list[str]) -> list[list[float]]:
            return [list(map(float, vector)) for vector in model.embed(texts)]

    return _Local()


def _why(shared: list[str], mode: str) -> str:
    named = ", ".join(tag.replace("_", " ") for tag in shared)
    return f"Same category; shared: {named}." + (" Reranked by embedding similarity." if mode == "embeddings" else "")


def _summary_of(case: Case, tags: set[str]) -> str:
    return f"{case.dispute.category.value.replace('_', ' ')}: " + ", ".join(sorted(t.replace("_", " ") for t in tags))


def _rerank(candidates, query_text, embedder):
    """The candidates ordered by cosine similarity to the query, or (None, why not) when no usable model is available."""
    if embedder is None:
        return None, "No embedding model is available, so precedents were ranked by tags only."
    try:
        vectors = embedder.embed([query_text, *[p.case_summary for p, _ in candidates]])
    except Exception as error:  # a model that fails to load or run must not stop a Case
        return None, f"The embedding model failed ({error}), so precedents were ranked by tags only."
    query, rest = vectors[0], vectors[1:]
    order = sorted(range(len(candidates)), key=lambda i: (-_cosine(query, rest[i]), candidates[i][0].precedent_id))
    return [candidates[i] for i in order], None


def _cosine(a: list[float], b: list[float]) -> float:
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / norm if norm else 0.0
