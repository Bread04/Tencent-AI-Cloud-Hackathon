"""The rules enforced in code, not by prompt (architecture.md section 4).

`citation_errors` returns plain sentences an agent can be shown and asked to fix.
"""

from src.contracts import citation_errors
from tests import builders as b

GPS = b.an_evidence_item(evidence_id="EV-GPS-1")
FARE = b.an_evidence_item(evidence_id="EV-FARE-1", source="fare")
NO_CHAT = b.an_evidence_item(evidence_id="EV-CHAT-1", source="chat", status="missing", content="No chat log found")
EVIDENCE = [GPS, FARE, NO_CHAT]
POLICY = [b.a_policy_clause(clause_id="NS-1")]


def test_a_submission_citing_only_what_it_was_given_has_no_errors():
    submission = b.a_submission(facts_relied_on=["EV-GPS-1"], missing_evidence_ids=["EV-CHAT-1"])

    assert citation_errors(submission, EVIDENCE, POLICY) == []


def test_a_submission_citing_an_evidence_id_that_does_not_exist_is_an_error():
    submission = b.a_submission(facts_relied_on=["EV-GPS-1", "EV-DASHCAM-9"])

    errors = citation_errors(submission, EVIDENCE, POLICY)

    assert len(errors) == 1
    assert "EV-DASHCAM-9" in errors[0]


def test_a_submission_citing_a_policy_clause_that_does_not_exist_is_an_error():
    submission = b.a_submission(policy_clause_ids=["NS-1", "NS-99"])

    errors = citation_errors(submission, EVIDENCE, POLICY)

    assert len(errors) == 1
    assert "NS-99" in errors[0]


def test_a_missing_item_cannot_be_relied_on_as_fact():
    submission = b.a_submission(facts_relied_on=["EV-CHAT-1"])

    errors = citation_errors(submission, EVIDENCE, POLICY)

    assert len(errors) == 1
    assert "EV-CHAT-1" in errors[0] and "missing" in errors[0]


def test_an_available_item_cannot_be_cited_as_missing():
    submission = b.a_submission(missing_evidence_ids=["EV-GPS-1"])

    errors = citation_errors(submission, EVIDENCE, POLICY)

    assert len(errors) == 1
    assert "EV-GPS-1" in errors[0]


def test_a_ruling_is_checked_everywhere_it_cites_evidence():
    ruling = b.a_ruling(
        cited_evidence_ids=["EV-GPS-1"],
        calculation={"formula": "fee reversed", "input_evidence_ids": ["EV-FARE-7"], "result": "5.00"},
        argument_assessments=[
            {
                "author": "driver_advocate",
                "argument": "The rider never replied in chat.",
                "verdict": "unproven",
                "reason": "There is no chat log.",
                "evidence_ids": ["EV-CHAT-1"],
            }
        ],
        own_findings=[{"finding": "The pickup pin was moved.", "evidence_ids": ["EV-PIN-2"]}],
        material_evidence=[{"key": "rider_position", "label": "Rider position", "evidence_ids": ["EV-RIDER-3"]}],
    )

    errors = " ".join(citation_errors(ruling, EVIDENCE, POLICY))

    for bad_id in ["EV-FARE-7", "EV-CHAT-1", "EV-PIN-2", "EV-RIDER-3"]:
        assert bad_id in errors
    assert "EV-GPS-1" not in errors


def test_a_ruling_citing_a_precedent_it_was_not_given_is_an_error():
    ruling = b.a_ruling(cited_precedent_ids=["PREC-1", "PREC-404"])

    errors = citation_errors(ruling, EVIDENCE + [FARE], POLICY, precedents=[b.a_precedent(precedent_id="PREC-1")])

    assert len(errors) == 1
    assert "PREC-404" in errors[0]
