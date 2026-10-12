"""Seam: run_dispute with the precedent switch (ticket 10). Precedent is advisory, shown identically to every agent, and cited by ID."""

import json

from src.agents.policy.precedents import retrieve_precedents, seeded_precedents
from src.contracts import CaseStatus, LogEventKind, Switches
from src.intake import load_catalog
from src.llm.stub import StubModel, load_replies
from src.orchestrator import run_dispute
from src.store import CaseStore
from src.tools.evidence import gather_evidence

ON = Switches(policy_precedent=True, escalation=True)


def scripted(dispute_id, **judge_overrides):
    replies = load_replies(dispute_id)
    replies["judge"] = {**replies["judge"], **judge_overrides}
    return StubModel({("CASE-0001", agent): reply for agent, reply in replies.items()})


def served_ids(dispute_id):
    catalog, store = load_catalog(), CaseStore()
    dispute = catalog.dispute(dispute_id)
    case = store.create_case(dispute)
    store.add_evidence(case.case_id, gather_evidence(dispute.trip_id, catalog), agent="evidence")
    store.seal_evidence(case.case_id)
    return [s.precedent.precedent_id for s in retrieve_precedents(store.get_case(case.case_id), seeded_precedents()).served]


def run(dispute_id="DISP-003", switches=ON, model=None, precedents=None):
    catalog, store = load_catalog(), CaseStore()
    model = model or scripted(dispute_id)
    case = run_dispute(catalog.dispute(dispute_id), store=store, model=model, catalog=catalog, switches=switches, precedents=precedents)
    return store, case, model


def prompt_for(model, agent):
    return json.dumps(next(c["messages"] for c in model.calls if c["agent"] == agent))


# --- Retrieval is part of the run, and logged ------------------------------------------------------------------------------


def test_with_the_switch_on_similar_precedents_are_retrieved_and_the_retrieval_is_logged_with_each_source():
    store, case, _ = run(model=scripted("DISP-003", precedent_departure="Unused.", cited_precedent_ids=[]))

    assert [p.precedent_id for p in case.precedents] == served_ids("DISP-003")
    event = next(e for e in store.log(case.case_id) if e.kind is LogEventKind.PRECEDENT_RETRIEVED)
    assert event.references == served_ids("DISP-003")
    assert "tags" in event.summary and "seeded" in event.summary


def test_the_advocates_and_the_judge_are_shown_the_same_precedents():
    _, _, model = run(model=scripted("DISP-003", precedent_departure="Unused."))

    for agent in ("rider_advocate", "driver_advocate", "judge"):
        text = prompt_for(model, agent)
        assert all(pid in text for pid in served_ids("DISP-003")), agent


def test_precedent_is_presented_as_advisory_and_carries_its_source_and_why():
    _, _, model = run(model=scripted("DISP-003", precedent_departure="Unused."))

    text = prompt_for(model, "judge")
    assert "advisory" in text and "seeded" in text and "Same category; shared:" in text


def test_when_no_precedent_is_found_the_judge_is_told_so_explicitly():
    _, _, model = run(precedents=[])

    assert "No precedent found for this Case." in prompt_for(model, "judge")
    assert "No precedent found for this Case." in prompt_for(model, "rider_advocate")


def test_with_the_switch_off_nothing_is_retrieved_and_the_judge_rules_from_policy_alone():
    store, case, model = run(switches=Switches(escalation=True), model=scripted("DISP-003"))

    assert case.precedents == [] and case.status is CaseStatus.NOTIFIED
    assert not [e for e in store.log(case.case_id) if e.kind is LogEventKind.PRECEDENT_RETRIEVED]
    assert "recedent" not in prompt_for(model, "judge")


# --- Citing precedent ------------------------------------------------------------------------------------------------------------


def test_a_ruling_can_cite_a_precedent_it_was_shown():
    cited = served_ids("DISP-003")[0]

    _, case, _ = run(model=scripted("DISP-003", cited_precedent_ids=[cited], precedent_departure="Differs from the others: only four minutes passed."))

    assert case.ruling.cited_precedent_ids == [cited]


def test_a_citation_to_a_precedent_that_was_not_shown_is_rejected_and_the_case_goes_to_review():
    _, case, _ = run(model=scripted("DISP-003", cited_precedent_ids=["PREC-NOPE-9"], precedent_departure="Unused."))

    assert case.status is CaseStatus.PENDING_REVIEW and case.ruling is None


def test_a_remedy_that_differs_from_a_shown_precedent_with_no_explanation_is_sent_back_and_then_held_for_review():
    store, case, model = run(model=scripted("DISP-003", precedent_departure=None))

    assert case.status is CaseStatus.PENDING_REVIEW and case.ruling is None
    escalation = next(e for e in store.log(case.case_id) if e.kind is LogEventKind.ESCALATED)
    assert "precedent_departure" in escalation.summary
    assert len([c for c in model.calls if c["agent"] == "judge"]) == 3  # the first try and two repairs


def test_an_explained_departure_is_accepted_and_shown_in_the_ruling():
    _, case, _ = run(model=scripted("DISP-003", precedent_departure="Here only four minutes passed, unlike the precedent."))

    assert case.ruling is not None
    assert "Departs from precedent: Here only four minutes passed" in case.ruling.reasoning_summary


def test_following_every_shown_precedent_needs_no_explanation():
    same = [p for p in seeded_precedents() if p.precedent_id == "PREC-NS-02"]

    _, case, _ = run(precedents=same, model=scripted("DISP-003", precedent_departure=None, cited_precedent_ids=["PREC-NS-02"]))

    assert case.ruling is not None and case.ruling.cited_precedent_ids == ["PREC-NS-02"]


# --- A Safety Incident with precedent ----------------------------------------------------------------------------------------------


def test_a_safety_incident_is_served_safety_precedents_and_the_ruling_cites_one_and_still_goes_to_a_person():
    switches = Switches(policy_precedent=True, sla_routing=True, escalation=True)
    catalog, store = load_catalog(), CaseStore()
    from src.api.demo import ReplayModel

    case = run_dispute(catalog.dispute("DISP-005"), store=store, model=ReplayModel(store), catalog=catalog, switches=switches)

    assert case.precedents and {p.category.value for p in case.precedents} == {"safety_incident"}
    assert "PREC-SF-01" in case.ruling.cited_precedent_ids
    assert case.status is CaseStatus.PENDING_REVIEW  # a Safety Incident is always held, with or without precedent
