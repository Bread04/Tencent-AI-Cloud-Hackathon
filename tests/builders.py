"""Valid example contract objects for tests. Override any field by keyword."""

from datetime import datetime, timezone

from src import contracts as c

FILED_AT = datetime(2026, 10, 9, 8, 30, tzinfo=timezone.utc)


def a_dispute(**overrides):
    fields = dict(
        dispute_id="DISP-002",
        trip_id="TRIP-002",
        filed_by="rider",
        category="no_show_charge",
        description="The driver did not show up but I was charged a cancellation fee.",
        requested_remedy="Reverse the no-show fee",
        filed_at=FILED_AT,
    )
    return c.Dispute(**(fields | overrides))


def an_evidence_item(**overrides):
    fields = dict(
        evidence_id="EV-GPS-1",
        source="gps",
        trip_id="TRIP-002",
        side="shared",
        timestamp=FILED_AT,
        status="available",
        content="Driver was 40 m from the pickup point at 08:02.",
        derived={"distance_to_pickup_m": 40},
    )
    return c.EvidenceItem(**(fields | overrides))


def a_submission(**overrides):
    fields = dict(
        author="rider_advocate",
        claim_restated="The no-show fee should be reversed because the driver never reached the pickup point.",
        facts_relied_on=["EV-GPS-1"],
        counter_arguments=[
            {"argument": "The driver waited the full free-wait period.", "response": "The timer started 300 m away."}
        ],
        policy_clause_ids=["NS-1"],
        requested_outcome="Reverse the no-show fee in full.",
    )
    return c.Submission(**(fields | overrides))


def a_policy_clause(**overrides):
    fields = dict(
        clause_id="NS-1",
        category="no_show_charge",
        text="A no-show fee applies only if the driver waited at the pickup point for the free-wait period.",
        version="mock-1",
    )
    return c.PolicyClause(**(fields | overrides))


def a_ruling(**overrides):
    fields = dict(
        status="final",
        outcome="uphold",
        balance_of_evidence="claimant",
        remedy="fee_reversal",
        amount="5.00",
        currency="SGD",
        calculation={
            "formula": "no-show fee charged, reversed in full",
            "input_evidence_ids": ["EV-FARE-1"],
            "result": "5.00",
        },
        argument_assessments=[
            {
                "author": "rider_advocate",
                "argument": "The driver never reached the pickup point.",
                "verdict": "accepted",
                "reason": "GPS places the driver 300 m away throughout the wait.",
                "evidence_ids": ["EV-GPS-1"],
            }
        ],
        policy_fit="clear",
        policy_fit_reason="NS-1 requires the driver to wait at the pickup point.",
        cited_evidence_ids=["EV-GPS-1", "EV-FARE-1"],
        cited_policy_clause_ids=["NS-1"],
        reasoning_summary="The driver did not wait at the pickup point, so the fee is reversed.",
        confidence={"value": 0.95, "components": {"policy_fit": 0.95, "evidence_completeness": 1.0}},
        material_evidence=[
            {"key": "driver_at_pickup", "label": "Driver position at the pickup point", "evidence_ids": ["EV-GPS-1"]}
        ],
    )
    return c.Ruling(**(fields | overrides))


def a_precedent(**overrides):
    fields = dict(
        precedent_id="PREC-1",
        case_summary="Rider charged a no-show fee; driver's GPS never reached the pickup point.",
        ruling=a_ruling(),
        source="model",
        category="no_show_charge",
        similarity_tags=["driver_not_at_pickup"],
    )
    return c.Precedent(**(fields | overrides))


def an_outcome(**overrides):
    fields = dict(
        party="rider",
        ruling_summary="Your claim was upheld. The SGD 5.00 no-show fee will be reversed.",
        action_status="recommended",
    )
    return c.Outcome(**(fields | overrides))


def a_log_event(**overrides):
    fields = dict(
        case_id="CASE-0001",
        timestamp=FILED_AT,
        agent="rider_advocate",
        kind="submission_filed",
        summary="Rider Advocate filed its Submission.",
        references=["EV-GPS-1", "NS-1"],
    )
    return c.LogEvent(**(fields | overrides))


def a_case(**overrides):
    fields = dict(case_id="CASE-0001", dispute=a_dispute(), created_at=FILED_AT, updated_at=FILED_AT)
    return c.Case(**(fields | overrides))
