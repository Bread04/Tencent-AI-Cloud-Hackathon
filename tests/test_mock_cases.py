"""The three No-Show mock cases run end to end on scripted replies and are checked against `data/cases/*.eval.json`.

Scripted, so this verifies the Judge's rules on the real case data (amount, Confidence, review routing, remedy list),
not the model's judgement. The same labels are checked against a real model by the evaluation harness (ticket 20).
"""

import json
from decimal import Decimal

import pytest

from src.config import CONFIG
from src.contracts import CaseStatus, RulingOutcome, RulingStatus
from src.intake import DEFAULT_DATA_DIR, load_catalog
from src.orchestrator import run_dispute
from src.store import CaseStore

from tests.cases import a_stub_for


def label(dispute_id: str) -> dict:
    return json.loads((DEFAULT_DATA_DIR / f"{dispute_id.lower()}.eval.json").read_text(encoding="utf-8"))


def run(dispute_id: str):
    catalog = load_catalog()
    return run_dispute(catalog.dispute(dispute_id), store=CaseStore(), model=a_stub_for("CASE-0001", dispute_id), catalog=catalog)


@pytest.mark.parametrize("dispute_id", ["DISP-002", "DISP-003"])
def test_a_decided_mock_case_matches_its_expected_outcome_remedy_and_amount(dispute_id):
    expected = label(dispute_id)

    case = run(dispute_id)

    assert case.status is CaseStatus.NOTIFIED
    assert case.ruling.outcome is RulingOutcome(expected["expected_outcome"])
    assert case.ruling.remedy.value == expected["expected_remedy"]
    assert case.ruling.amount == (Decimal(expected["expected_amount"]) if "expected_amount" in expected else None)


def test_the_claimant_wins_mock_case_stays_above_the_escalation_threshold():
    assert run("DISP-003").ruling.confidence.value >= CONFIG.escalation.confidence_threshold


def test_the_respondent_wins_demo_case_stays_at_the_escalation_threshold_after_history():
    assert run("DISP-002").ruling.confidence.value >= CONFIG.escalation.confidence_threshold


def test_the_ambiguous_mock_case_is_held_for_review_below_the_escalation_threshold():
    expected = label("DISP-004")

    case = run("DISP-004")

    assert case.ruling.status is RulingStatus.PROPOSAL  # a proposal, not a final decision
    assert case.status is CaseStatus.PENDING_REVIEW
    assert case.ruling.amount is None  # nothing is authorised before review
    assert case.ruling.confidence.value < CONFIG.escalation.confidence_threshold
    triggers = {record.trigger.value for record in case.ruling.review_triggers}
    assert triggers & set(expected["acceptable_review_triggers"])
