"""Seam: outcomes_for(ruling, case) -> one Outcome per party, written by a template from the finished Ruling."""

from src.agents.outcomes import outcomes_for
from src.contracts import ActionStatus, Party

from tests.builders import a_ruling
from tests.cases import a_sealed_no_show_case

_, CASE = a_sealed_no_show_case()  # the rider is the Claimant

REJECTED = dict(outcome="reject", balance_of_evidence="respondent", remedy="no_action", amount=None, currency=None, calculation=None)


def outcomes(ruling):
    return {outcome.party: outcome for outcome in outcomes_for(ruling, CASE)}


def test_each_party_gets_exactly_one_outcome():
    result = outcomes_for(a_ruling(), CASE)

    assert sorted(o.party for o in result) == sorted(Party)


def test_an_upheld_claim_tells_both_parties_the_fee_is_reversed_and_how_much():
    result = outcomes(a_ruling())  # upheld, fee reversal of SGD 5.00

    assert "upheld" in result[Party.RIDER].ruling_summary and "SGD 5.00" in result[Party.RIDER].ruling_summary
    assert "upheld" in result[Party.DRIVER].ruling_summary and "SGD 5.00" in result[Party.DRIVER].ruling_summary
    assert "reversed" in result[Party.RIDER].ruling_summary


def test_each_outcome_is_worded_for_its_party():
    result = outcomes(a_ruling())

    assert "Your claim" in result[Party.RIDER].ruling_summary  # the rider filed it
    assert "Your claim" not in result[Party.DRIVER].ruling_summary
    assert "The rider's claim" in result[Party.DRIVER].ruling_summary


def test_a_rejected_claim_tells_both_parties_the_fee_stands_with_the_reason():
    ruling = a_ruling(**REJECTED, reasoning_summary="The driver waited the full window.")

    result = outcomes(ruling)

    for party in Party:
        assert "not upheld" in result[party].ruling_summary and "stands" in result[party].ruling_summary
        assert "The driver waited the full window." in result[party].ruling_summary


def test_a_final_ruling_is_only_recommended_never_executed():
    assert {o.action_status for o in outcomes_for(a_ruling(), CASE)} == {ActionStatus.RECOMMENDED}


def test_a_proposal_tells_both_parties_review_is_pending_without_giving_the_proposed_outcome():
    ruling = a_ruling(status="proposal", **REJECTED)

    for outcome in outcomes_for(ruling, CASE):
        assert outcome.action_status is ActionStatus.PENDING_REVIEW
        assert "review" in outcome.ruling_summary.lower() and "pending" in outcome.ruling_summary.lower()
        assert "not upheld" not in outcome.ruling_summary and "reversed" not in outcome.ruling_summary
