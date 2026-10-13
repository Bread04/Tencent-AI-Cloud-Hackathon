"""The Learning Feedback Loop (ticket 16, ADR 0003): a Human Reviewer's Override becomes a Precedent.

Only an Override teaches: it is the case where a person disagreed with the system. The Precedent says what the
Case looked like (its tags, never the parties or the trip), what the reviewer decided and why. Policy text is
never changed here; a Precedent is advisory, and the Judge may still depart from it with an explanation.
"""

from src.agents.policy.precedents import case_tags
from src.contracts import Case, Confidence, LogEventKind, Precedent, PrecedentSource, Ruling
from src.store import CaseStore


def learn_from_override(store: CaseStore, case: Case, final: Ruling, reason: str) -> None:
    """Add the Override to the precedent store, or log why it could not be. Call only with the learning switch on."""
    tags = sorted(case_tags(case))
    if not tags:  # a category with no tag vocabulary yet could never be retrieved, so storing it would only be noise
        store.log_event(
            case.case_id, "learning", LogEventKind.PRECEDENT_ADDED,
            f"No Precedent added: {case.dispute.category.value} Cases have no similarity tags yet, so it could not be retrieved.",
        )
        return
    store.add_human_precedent(case.case_id, lambda precedent_id: precedent_from(case, final, reason, tags, precedent_id))


def precedent_from(case: Case, final: Ruling, reason: str, tags: list[str], precedent_id: str) -> Precedent:
    """Anonymised: no evidence, party, trip or History detail from the Case survives into the Precedent."""
    category = case.dispute.category.value.replace("_", " ")
    named = ", ".join(tag.replace("_", " ") for tag in tags)
    ruling = final.model_copy(
        update={
            "argument_assessments": [],
            "own_findings": [],
            "cited_evidence_ids": [],
            "missing_evidence_ids": [],
            "history_adjustments": [],
            "material_evidence": [],
            "review_triggers": [],
            "policy_gap": None,
            "policy_fit_reason": "A Human Reviewer decided this Case.",  # the Judge's own reason describes the Case it ruled on
            "confidence": Confidence(value=1.0, components={"human_review": 1.0}),  # a person decided it
            "reasoning_summary": f"A Human Reviewer overrode the proposed Ruling. Reason: {reason}",
        }
    )
    return Precedent(
        precedent_id=precedent_id,
        case_summary=f"{category.capitalize()} Case: {named}. A Human Reviewer overrode the proposed Ruling.",
        ruling=ruling,
        source=PrecedentSource.HUMAN_OVERRIDE,
        override_reason=reason,
        category=case.dispute.category,
        similarity_tags=tags,
    )
