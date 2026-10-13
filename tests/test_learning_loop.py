"""Seam: decide_review(...) with the learning-loop switch, and run_dispute's precedent retrieval (ticket 16).

An Override becomes a Precedent marked as coming from a human, retrievable by a later similar Case. Policy is never touched.
"""

import json
import re

import pytest

from src.agents.escalation import decide_review
from src.agents.policy import policy_for
from src.api.demo import ReplayModel
from src.contracts import CaseStatus, LogEventKind, PrecedentSource, ReviewDecision, Switches
from src.intake import load_catalog
from src.orchestrator import run_dispute
from src.store import CaseStore

from tests.test_precedents import FORBIDDEN

REASON = "The driver's GPS stops after 09:02, so presence for the full wait is not established."
LEARNING = Switches(escalation=True, policy_precedent=True, learning_loop=True)
NOT_LEARNING = LEARNING.model_copy(update={"learning_loop": False})


def held_case(switches=LEARNING, store=None):
    """DISP-004 on the scripted replies: it is held for review on low Confidence."""
    catalog, store = load_catalog(), store or CaseStore()
    case = run_dispute(catalog.dispute("DISP-004"), store=store, model=ReplayModel(store), catalog=catalog, switches=switches)
    assert case.status is CaseStatus.PENDING_REVIEW
    return store, case


def override(store, case, reason=REASON):
    return decide_review(store, case.case_id, reviewer="Dana", decision=ReviewDecision.OVERRIDE, reason=reason)


# --- An Override creates a Precedent -----------------------------------------------------------------------------------


def test_an_override_adds_a_precedent_from_a_human_override_carrying_the_reason():
    store, case = held_case()

    override(store, case)

    [precedent] = store.human_precedents()
    assert precedent.source is PrecedentSource.HUMAN_OVERRIDE
    assert precedent.override_reason == REASON
    assert precedent.category is case.dispute.category
    assert precedent.similarity_tags  # described in the vocabulary retrieval ranks by
    assert precedent.ruling.outcome.value == "uphold"  # the proposal was to reject, so the override is the other outcome


def test_the_communication_log_records_the_new_precedent():
    store, case = held_case()

    override(store, case)

    event = next(e for e in store.log(case.case_id) if e.kind is LogEventKind.PRECEDENT_ADDED)
    [precedent] = store.human_precedents()
    assert event.references == [precedent.precedent_id]
    assert "override" in event.summary.lower()


def test_a_confirmation_adds_no_precedent():
    store, case = held_case()

    decide_review(store, case.case_id, reviewer="Dana", decision=ReviewDecision.CONFIRM)

    assert store.human_precedents() == []


def test_with_the_switch_off_the_override_is_recorded_but_no_precedent_is_added():
    store, case = held_case(NOT_LEARNING)

    decided = override(store, case)

    assert decided.review_record.reason == REASON and decided.review_record.decision is ReviewDecision.OVERRIDE
    assert store.human_precedents() == []
    assert not [e for e in store.log(case.case_id) if e.kind is LogEventKind.PRECEDENT_ADDED]


def test_the_precedent_holds_no_party_identifier_trip_id_reviewer_or_history_derived_fact():
    store, case = held_case()

    override(store, case)

    text = store.human_precedents()[0].model_dump_json()
    for pattern in FORBIDDEN:
        assert not pattern.search(text), pattern.pattern
    assert "Dana" not in text and case.dispute.trip_id not in text


def test_policy_clauses_are_unchanged_by_an_override():
    store, case = held_case()
    before = policy_for(case.dispute.category)

    decided = override(store, case)

    assert policy_for(case.dispute.category) == before
    assert decided.policy_clauses == case.policy_clauses


def test_each_override_gets_its_own_precedent_id():
    store, first = held_case()
    override(store, first)
    _, second = held_case(LEARNING.model_copy(update={"policy_precedent": False}), store)  # no precedent shown: the script has no departure to explain

    override(store, second)

    ids = [p.precedent_id for p in store.human_precedents()]
    assert len(ids) == 2 and len(set(ids)) == 2
    assert all(re.fullmatch(r"PREC-HO-\d{4}", i) for i in ids)


# --- A later similar Case retrieves and cites it ----------------------------------------------------------------------------------


def later_case(store, switches=LEARNING):
    catalog = load_catalog()
    return run_dispute(catalog.dispute("DISP-007"), store=store, model=ReplayModel(store), catalog=catalog, switches=switches)


def test_a_later_similar_case_retrieves_the_override_and_the_judge_cites_it():
    store, case = held_case()
    override(store, case)
    [precedent] = store.human_precedents()

    later = later_case(store)

    served = {p.precedent_id: p for p in later.precedents}
    assert served[precedent.precedent_id].source is PrecedentSource.HUMAN_OVERRIDE
    assert precedent.precedent_id in later.ruling.cited_precedent_ids
    event = next(e for e in store.log(later.case_id) if e.kind is LogEventKind.PRECEDENT_RETRIEVED)
    assert "human_override" in event.summary


def test_the_judge_is_shown_the_reviewers_reason():
    store, case = held_case()
    override(store, case)
    model = ReplayModel(store)
    catalog = load_catalog()

    run_dispute(catalog.dispute("DISP-007"), store=store, model=model, catalog=catalog, switches=LEARNING)

    prompts = [c for c in model.calls if c["agent"] == "judge"]
    assert prompts and REASON in json.dumps(prompts[0]["messages"])


def test_without_an_override_the_later_case_is_served_only_seeded_precedents():
    store = CaseStore()

    later = later_case(store)

    assert later.precedents and {p.source for p in later.precedents} == {PrecedentSource.SEEDED}


def test_with_the_switch_off_the_later_case_does_not_see_the_override():
    store, case = held_case(NOT_LEARNING)
    override(store, case)

    later = later_case(store, NOT_LEARNING)

    assert PrecedentSource.HUMAN_OVERRIDE not in {p.source for p in later.precedents}
