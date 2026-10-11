"""The Case store: the one shared state. Every write emits exactly one Log event."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.contracts import Switches
from src.store import CaseNotFound, CaseStore, StoreError
from tests import builders as b

GPS = b.an_evidence_item(evidence_id="EV-GPS-1")
FARE = b.an_evidence_item(evidence_id="EV-FARE-1", source="fare")


def kinds(store, case_id):
    return [event.kind for event in store.log(case_id)]


def a_case_with_sealed_evidence(store):
    case = store.create_case(b.a_dispute())
    store.add_evidence(case.case_id, [GPS, FARE], agent="orchestrator")
    store.seal_evidence(case.case_id)
    return case.case_id


def test_create_write_read_back_and_see_one_log_event_per_write():
    store = CaseStore()

    case = store.create_case(b.a_dispute())
    assert len(store.log(case.case_id)) == 1

    store.add_evidence(case.case_id, [GPS], agent="rider_evidence_agent")
    assert len(store.log(case.case_id)) == 2

    store.seal_evidence(case.case_id)
    assert len(store.log(case.case_id)) == 3

    store.add_submission(case.case_id, b.a_submission(author="rider_advocate"))
    assert len(store.log(case.case_id)) == 4

    read_back = store.get_case(case.case_id)
    assert read_back.dispute == b.a_dispute()
    assert read_back.evidence == [GPS]
    assert read_back.submissions == [b.a_submission(author="rider_advocate")]
    assert kinds(store, case.case_id) == ["case_filed", "evidence_returned", "evidence_sealed", "submission_filed"]


def test_a_new_case_is_filed_with_the_configured_switches_all_off():
    store = CaseStore()

    case = store.create_case(b.a_dispute())

    assert case.status == "filed"
    assert case.switches == Switches()
    assert not any(case.switches.model_dump().values())


def test_a_case_can_be_created_with_chosen_switches_in_force():
    store = CaseStore()

    case = store.create_case(b.a_dispute(), switches=Switches(escalation=True))

    assert store.get_case(case.case_id).switches.escalation is True


def test_each_case_gets_its_own_id_and_its_own_log():
    store = CaseStore()

    first = store.create_case(b.a_dispute(dispute_id="DISP-001"))
    second = store.create_case(b.a_dispute(dispute_id="DISP-002"))
    store.add_evidence(second.case_id, [GPS], agent="orchestrator")

    assert first.case_id != second.case_id
    assert len(store.log(first.case_id)) == 1
    assert len(store.log(second.case_id)) == 2
    assert {event.case_id for event in store.log(second.case_id)} == {second.case_id}
    assert [case.case_id for case in store.list_cases()] == [first.case_id, second.case_id]


def test_log_events_say_who_did_what_and_reference_the_ids_involved():
    store = CaseStore()
    case = store.create_case(b.a_dispute())

    store.add_evidence(case.case_id, [GPS, FARE], agent="driver_evidence_agent")

    event = store.log(case.case_id)[-1]
    assert event.agent == "driver_evidence_agent"
    assert event.kind == "evidence_returned"
    assert event.references == ["EV-GPS-1", "EV-FARE-1"]
    assert event.summary


def test_log_events_and_the_case_carry_the_time_of_the_write():
    ticks = iter(datetime(2026, 10, 9, 9, 0, tzinfo=timezone.utc) + timedelta(minutes=n) for n in range(10))
    store = CaseStore(clock=lambda: next(ticks))

    case = store.create_case(b.a_dispute())
    store.add_evidence(case.case_id, [GPS], agent="orchestrator")

    created, written = (event.timestamp for event in store.log(case.case_id))
    assert written - created == timedelta(minutes=1)
    assert store.get_case(case.case_id).created_at == created
    assert store.get_case(case.case_id).updated_at == written


def test_the_case_moves_through_its_lifecycle_as_it_is_written_to():
    store = CaseStore()
    case_id = store.create_case(b.a_dispute()).case_id
    assert store.get_case(case_id).status == "filed"

    store.set_priority(case_id, 1, reason="All Cases share one priority while SLA routing is off.")
    assert store.get_case(case_id).status == "prioritised"

    store.add_evidence(case_id, [GPS, FARE], agent="orchestrator")
    assert store.get_case(case_id).status == "gathering_evidence"

    store.seal_evidence(case_id)
    assert store.get_case(case_id).status == "building_cases"

    store.add_policy_clauses(case_id, [b.a_policy_clause()], agent="orchestrator")
    store.add_submission(case_id, b.a_submission(author="rider_advocate"))
    assert store.get_case(case_id).status == "building_cases"

    store.add_submission(case_id, b.a_submission(author="driver_advocate"))
    assert store.get_case(case_id).status == "judging"

    store.set_ruling(case_id, b.a_ruling(status="final"))
    assert store.get_case(case_id).status == "ruled"

    store.add_outcome(case_id, b.an_outcome(party="rider"))
    assert store.get_case(case_id).status == "ruled"

    store.add_outcome(case_id, b.an_outcome(party="driver"))
    assert store.get_case(case_id).status == "notified"

    assert kinds(store, case_id) == [
        "case_filed",
        "priority_set",
        "evidence_returned",
        "evidence_sealed",
        "policy_retrieved",
        "submission_filed",
        "submission_filed",
        "ruling_drafted",
        "outcome_sent",
        "outcome_sent",
    ]


def test_a_proposed_ruling_is_stored_but_the_case_is_not_ruled():
    store = CaseStore()
    case_id = a_case_with_sealed_evidence(store)
    store.add_submission(case_id, b.a_submission(author="rider_advocate"))
    store.add_submission(case_id, b.a_submission(author="driver_advocate"))

    store.set_ruling(case_id, b.a_ruling(status="proposal"))

    case = store.get_case(case_id)
    assert case.ruling.status == "proposal"
    assert case.status == "judging"


def test_rejecting_a_case_records_why():
    store = CaseStore()
    case_id = store.create_case(b.a_dispute()).case_id

    store.reject_case(case_id, reason="Trip TRIP-002 does not exist.")

    assert store.get_case(case_id).status == "rejected"
    assert store.log(case_id)[-1].kind == "case_rejected"
    assert "TRIP-002 does not exist" in store.log(case_id)[-1].summary


def test_sealing_gives_the_evidence_set_a_version_and_freezes_it():
    store = CaseStore()
    case_id = store.create_case(b.a_dispute()).case_id
    store.add_evidence(case_id, [GPS], agent="orchestrator")
    assert store.get_case(case_id).evidence_version is None

    store.seal_evidence(case_id)
    version = store.get_case(case_id).evidence_version
    assert version

    with pytest.raises(StoreError) as error:
        store.add_evidence(case_id, [FARE], agent="orchestrator")

    assert "sealed" in str(error.value)
    assert store.get_case(case_id).evidence == [GPS]
    assert version in store.log(case_id)[-1].references


def test_a_submission_cannot_be_filed_before_the_evidence_is_sealed():
    store = CaseStore()
    case_id = store.create_case(b.a_dispute()).case_id

    with pytest.raises(StoreError) as error:
        store.add_submission(case_id, b.a_submission())

    assert "sealed" in str(error.value)


def test_a_refused_write_changes_nothing_and_logs_nothing():
    store = CaseStore()
    case_id = a_case_with_sealed_evidence(store)
    store.add_submission(case_id, b.a_submission(author="rider_advocate"))
    events_before = len(store.log(case_id))

    with pytest.raises(ValidationError) as error:
        store.add_submission(case_id, b.a_submission(author="rider_advocate"))

    assert "rider_advocate" in str(error.value)
    assert len(store.get_case(case_id).submissions) == 1
    assert len(store.log(case_id)) == events_before


def test_two_evidence_items_cannot_share_an_id():
    store = CaseStore()
    case_id = store.create_case(b.a_dispute()).case_id
    store.add_evidence(case_id, [GPS], agent="orchestrator")

    with pytest.raises(StoreError) as error:
        store.add_evidence(case_id, [GPS], agent="orchestrator")

    assert "EV-GPS-1" in str(error.value)


def test_an_event_with_no_state_change_can_be_logged():
    store = CaseStore()
    case_id = store.create_case(b.a_dispute()).case_id

    store.log_event(case_id, agent="rider_advocate", kind="evidence_requested", summary="Asked for the GPS trace.")

    assert kinds(store, case_id) == ["case_filed", "evidence_requested"]


def test_what_is_read_from_the_store_cannot_change_the_store():
    store = CaseStore()
    case_id = store.create_case(b.a_dispute()).case_id

    store.get_case(case_id).evidence.append(GPS)
    store.log(case_id).clear()

    assert store.get_case(case_id).evidence == []
    assert len(store.log(case_id)) == 1


def test_an_unknown_case_id_is_a_clear_error():
    store = CaseStore()

    with pytest.raises(CaseNotFound) as error:
        store.get_case("CASE-9999")

    assert "CASE-9999" in str(error.value)


def test_changing_an_object_after_handing_it_to_the_store_does_not_change_the_case():
    store = CaseStore()
    case_id = store.create_case(b.a_dispute()).case_id
    item = b.an_evidence_item(evidence_id="EV-GPS-9")
    store.add_evidence(case_id, [item], agent="orchestrator")
    store.seal_evidence(case_id)

    item.status = "missing"
    item.content = "tampered after sealing"

    stored = store.get_case(case_id).evidence[0]
    assert stored.status == "available"
    assert stored.content != "tampered after sealing"


def test_a_log_event_read_from_the_store_cannot_be_edited_in_place():
    store = CaseStore()
    case_id = store.create_case(b.a_dispute()).case_id

    store.log(case_id)[0].summary = "rewritten"

    assert store.log(case_id)[0].summary != "rewritten"


def test_priority_can_only_be_set_on_a_newly_filed_case():
    store = CaseStore()
    case_id = a_case_with_sealed_evidence(store)

    with pytest.raises(StoreError, match="building_cases"):
        store.set_priority(case_id, 1, reason="Too late.")

    assert store.get_case(case_id).status == "building_cases"


def test_a_case_can_only_be_rejected_at_intake():
    store = CaseStore()
    case_id = a_case_with_sealed_evidence(store)

    with pytest.raises(StoreError, match="building_cases"):
        store.reject_case(case_id, reason="Too late.")


def test_a_rejected_case_accepts_no_further_writes():
    store = CaseStore()
    case_id = store.create_case(b.a_dispute()).case_id
    store.reject_case(case_id, reason="Trip TRIP-002 does not exist.")

    with pytest.raises(StoreError, match="rejected"):
        store.add_evidence(case_id, [GPS], agent="orchestrator")

    assert kinds(store, case_id) == ["case_filed", "case_rejected"]


def test_a_ruling_needs_both_submissions():
    store = CaseStore()
    case_id = a_case_with_sealed_evidence(store)
    store.add_submission(case_id, b.a_submission(author="rider_advocate"))

    with pytest.raises(StoreError, match="both Submissions"):
        store.set_ruling(case_id, b.a_ruling())

    assert store.get_case(case_id).ruling is None


def test_two_policy_clauses_cannot_share_an_id():
    store = CaseStore()
    case_id = store.create_case(b.a_dispute()).case_id
    store.add_policy_clauses(case_id, [b.a_policy_clause(clause_id="NS-1")], agent="orchestrator")

    with pytest.raises(StoreError, match="NS-1"):
        store.add_policy_clauses(case_id, [b.a_policy_clause(clause_id="NS-1")], agent="orchestrator")
