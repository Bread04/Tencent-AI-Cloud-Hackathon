"""Seam: the Rider and Driver Evidence Agents (ticket 11). They read only party-written text, ground every fact in a real message, and are switched."""

import json

import pytest

from src.agents.evidence_agents import ExtractedFact, ExtractedFacts, gather_evidence_safely, message_refs, run_evidence_agent
from src.contracts import CaseStatus, EvidenceStatus, LogEventKind, Party, Switches
from src.intake import load_catalog
from src.llm import ModelError, StubModel
from src.orchestrator import run_dispute
from src.store import CaseStore
from src.tools.evidence import gather_evidence

ON = Switches(evidence_agents=True, escalation=True)


def a_case(dispute_id="DISP-002", switches=ON):
    catalog, store = load_catalog(), CaseStore()
    dispute = catalog.dispute(dispute_id)
    case = store.create_case(dispute, switches)
    store.add_evidence(case.case_id, gather_evidence(dispute.trip_id, catalog), agent="evidence")
    return store.get_case(case.case_id)


def facts(*pairs):
    return ExtractedFacts(facts=[ExtractedFact(source_ref=ref, quote=quote, fact=fact) for ref, quote, fact in pairs]).model_dump()


def run_agent(side, reply, dispute_id="DISP-002"):
    case = a_case(dispute_id)
    model = StubModel({(case.case_id, f"{side.value}_evidence_agent"): reply})
    return case, model, run_evidence_agent(side, case, model)


# --- Each agent writes Evidence Items for its side, grounded in a message ---------------------------------------------------------------


def test_each_message_gets_a_reference_so_a_fact_can_point_at_it():
    refs = message_refs(a_case("DISP-003"))

    assert refs["EV-CHAT-1#1"].startswith("I am at the booked pickup bay")
    assert "DISPUTE#description" in refs and "DISPUTE#driver_statement" in refs


def test_an_agent_turns_what_it_read_into_evidence_items_for_its_side_that_point_at_the_message():
    case = a_case("DISP-003")
    refs = message_refs(case)
    quote = "I am coming to the pickup bay"
    ref = next(r for r, text in refs.items() if quote in text)

    _, _, items = run_agent(Party.RIDER, facts((ref, quote, "The rider said they were on their way.")), "DISP-003")

    (item,) = items
    assert item.evidence_id == "EV-FACT-RIDER-1" and item.side.value == "rider" and item.source == "extracted_fact"
    assert item.status is EvidenceStatus.AVAILABLE and item.content == "The rider said they were on their way."
    assert item.derived["message_ref"] == ref and item.derived["quote"] == quote


def test_both_agents_read_the_same_text_and_are_told_it_is_untrusted_data():
    case = a_case("DISP-003")
    model = StubModel({(case.case_id, "rider_evidence_agent"): facts(), (case.case_id, "driver_evidence_agent"): facts()})

    run_evidence_agent(Party.RIDER, case, model)
    run_evidence_agent(Party.DRIVER, case, model)

    rider_prompt, driver_prompt = (json.dumps(c["messages"]) for c in model.calls)
    assert "untrusted" in rider_prompt and "untrusted" in driver_prompt
    assert "I cannot see you yet" in rider_prompt and "I cannot see you yet" in driver_prompt  # the same text
    assert "rider" in rider_prompt and "driver" in driver_prompt  # the only difference is whose position it serves


def test_a_message_that_was_sent_is_not_treated_as_one_that_was_read():
    _, model, _ = run_agent(Party.DRIVER, facts())

    assert "not proof it was read" in json.dumps(model.calls[0]["messages"])


# --- A fact must be grounded --------------------------------------------------------------------------------------------------------------


def test_a_fact_that_cites_a_message_that_does_not_exist_is_rejected_and_the_agent_is_asked_to_fix_it():
    case = a_case("DISP-003")
    ref = next(iter(message_refs(case)))
    quote = message_refs(case)[ref][:20]
    model = StubModel({(case.case_id, "rider_evidence_agent"): [facts(("EV-CHAT-1#99", "anything", "A made-up fact.")), facts((ref, quote, "A real one."))]})

    items = run_evidence_agent(Party.RIDER, case, model)

    assert [i.content for i in items] == ["A real one."]  # the second try was accepted
    assert "EV-CHAT-1#99" in json.dumps(model.calls[1]["messages"])  # the first problem was fed back


def test_a_quote_that_is_not_in_the_message_it_names_is_rejected():
    case = a_case("DISP-003")
    ref = next(iter(message_refs(case)))

    items = run_evidence_agent(Party.RIDER, case, StubModel({(case.case_id, "rider_evidence_agent"): facts((ref, "words nobody wrote", "Invented."))}))

    assert [i.status for i in items] == [EvidenceStatus.MISSING]  # never an invented fact
    assert "words nobody wrote" in items[0].content


def test_an_agent_that_cannot_run_leaves_a_missing_item_with_the_cause_not_a_crash():
    case = a_case("DISP-003")

    class Dead:
        def complete(self, messages, *, case_id, agent, schema=None, images=None):
            raise ModelError("The model timed out after 120 seconds (agent rider_evidence_agent).")

    items = run_evidence_agent(Party.RIDER, case, Dead())

    (item,) = items
    assert item.status is EvidenceStatus.MISSING and item.evidence_id == "EV-FACTS-RIDER-1"
    assert "timed out" in item.content and item.side.value == "rider"


def test_a_tool_failure_becomes_a_missing_item_with_the_cause():
    catalog = load_catalog()

    def broken(trip_id, catalog):
        raise KeyError("gps_telemetry")

    items = gather_evidence_safely("TRIP-2026-09945", catalog, tools=broken)

    (item,) = items
    assert item.status is EvidenceStatus.MISSING and "gps_telemetry" in item.content and item.evidence_id == "EV-TOOLS-1"


# --- In a whole run -------------------------------------------------------------------------------------------------------------------------


def run(dispute_id, switches=ON):
    from src.api.demo import ReplayModel

    catalog, store = load_catalog(), CaseStore()
    model = ReplayModel(store)
    case = run_dispute(catalog.dispute(dispute_id), store=store, model=model, catalog=catalog, switches=switches)
    return store, case, model


def test_with_the_switch_on_the_evidence_agents_run_before_sealing_and_both_advocates_can_read_what_either_found():
    store, case, model = run("DISP-003")

    fact_ids = [i.evidence_id for i in case.evidence if i.source == "extracted_fact"]
    assert any("RIDER" in i for i in fact_ids) and any("DRIVER" in i for i in fact_ids)
    assert case.evidence_version  # sealed, with the facts inside
    for agent in ("rider_advocate", "driver_advocate", "judge"):
        prompt = json.dumps(next(c["messages"] for c in model.calls if c["agent"] == agent))
        assert all(i in prompt for i in fact_ids), agent
    writers = {e.agent for e in store.log(case.case_id) if e.kind is LogEventKind.EVIDENCE_RETURNED}
    assert {"rider_evidence", "driver_evidence"} <= writers


def test_with_the_switch_off_no_agent_runs_and_the_earlier_cases_resolve_as_before():
    store, case, model = run("DISP-003", Switches(escalation=True))

    assert not [i for i in case.evidence if i.source == "extracted_fact"]
    assert not [c for c in model.calls if c["agent"].endswith("_evidence_agent")]
    assert case.status is CaseStatus.NOTIFIED


def test_an_instruction_hidden_in_the_chat_is_recorded_as_evidence_and_does_not_change_the_ruling():
    _, hidden, _ = run("DISP-007")
    _, plain, _ = run("DISP-002")

    injected = [i for i in hidden.evidence if i.source == "extracted_fact" and "ignore" in (i.derived.get("quote") or "").lower()]
    assert injected, "the message should be on record as evidence"
    assert hidden.ruling.outcome is plain.ruling.outcome and hidden.ruling.remedy is plain.ruling.remedy  # reject, as for DISP-002
    assert hidden.status is plain.status
