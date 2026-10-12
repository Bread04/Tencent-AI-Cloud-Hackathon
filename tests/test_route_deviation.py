"""Ticket 06 arithmetic, trust boundaries, matrix and six-case replay regressions."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import json

import pytest

from src.agents.judge.arguments import arguments_in
from src.agents.judge.draft import JudgeDraft, draft_problems
from src.agents.judge.numbers import amount_for
from src.agents.policy import policy_for
from src.agents.prompting import evidence_for_prompt
from src.api.demo import ReplayModel, PREPARED_DISPUTES
from src.contracts import BalanceOfEvidence, DisputeCategory, Remedy, citation_errors
from src.intake import DEFAULT_DATA_DIR, Catalog, load_catalog
from src.orchestrator import run_dispute
from src.store import CaseStore
from src.tools.evidence import gather_evidence
from src.tools.evidence.route import analyze_route, analyze_fare, stop_candidates
from tests.cases import stub_replies


def record():
    return deepcopy(load_catalog().trip("TRIP-2026-ROUTE-008"))


def run(dispute_id, store=None, model=None, catalog=None):
    store = store or CaseStore()
    catalog = catalog or load_catalog()
    return run_dispute(catalog.dispute(dispute_id), store=store, model=model or ReplayModel(store), catalog=catalog)


def test_all_six_replay_in_varied_order_without_labels_or_cross_case_context():
    store = CaseStore()
    model = ReplayModel(store)
    for dispute_id in ["DISP-010", "DISP-003", "DISP-009", "DISP-002", "DISP-008", "DISP-004", "DISP-008", "DISP-009"]:
        case = run(dispute_id, store, model)
        expected = json.loads((DEFAULT_DATA_DIR / f"{dispute_id.lower()}.eval.json").read_text())
        assert case.ruling is not None
        if expected["expected_outcome"] is None:
            assert case.status == "pending_review" and case.ruling.status == "proposal"
        else:
            assert case.ruling.outcome == expected["expected_outcome"]
            assert case.ruling.remedy == expected["expected_remedy"]
        assert case.ruling.amount == (Decimal(expected["expected_amount"]) if "expected_amount" in expected else None)
        for doc in [*case.submissions, case.ruling]:
            assert citation_errors(doc, case.evidence, case.policy_clauses) == []
        assert all(item.trip_id == case.dispute.trip_id for item in case.evidence)
    prompts = json.dumps([call["messages"] for call in model.calls])
    for withheld in ["expected_outcome", "scenario_classification", "rider_history", "driver_history"]:
        assert withheld not in prompts, withheld
    for call in model.calls:
        for message in call["messages"]:
            # Provenance may name the input source; raw geometry must not be projected.
            assert '"vehicle_gps":' not in message["content"]
            assert '"road_baseline":' not in message["content"]
    assert {"DISP-008", "DISP-009", "DISP-010"} <= set(PREPARED_DISPUTES)


def test_route_metrics_stop_and_fare_breakdown_are_citable_and_provenanced():
    raw = record()
    route, fare = analyze_route(raw), analyze_fare(raw, analyze_route(raw))
    assert route["available"] and fare["available"]
    assert Decimal(route["actual_km"]) > Decimal(route["optimal_km"])
    assert route["actual_minutes"] == "20.00" and route["expected_minutes"] == "12.00"
    assert len(route["stop_candidates"]) == 1
    assert route["stop_candidates"][0]["observed_seconds"] == 180
    assert route["stop_candidates"][0]["purpose"] == "unknown"
    assert route["provenance"]["optimal"] == "route_baseline.points"
    assert route["landmark_observations"][0]["name"] == "Lavender MRT"
    assert route["landmark_observations"][0]["within_50m"] is True
    assert set(fare["breakdown"]) == {"base", "distance", "time", "surge", "booking", "tolls", "promo", "paid_net"}
    assert fare["tariff"]["surge"] == "1.20" and fare["tariff"]["promo"] == "2.00"
    items = gather_evidence(raw["trip"]["trip_id"], load_catalog())
    assert next(item for item in items if item.source == "rider_location").status == "missing"
    assert next(item for item in items if item.source == "route").derived["vehicle_gps_only"] is True


@pytest.mark.parametrize("dispute_id", ["DISP-008", "DISP-009", "DISP-010"])
def test_route_samples_complete_both_stability_passes(dispute_id):
    from src.config import CONFIG
    catalog, store = load_catalog(), CaseStore()
    model = ReplayModel(store)
    case = run_dispute(catalog.dispute(dispute_id), store=store, model=model, catalog=catalog, switches=CONFIG.switches.model_copy(update={"stability_check": True}))
    expected = json.loads((DEFAULT_DATA_DIR / f"{dispute_id.lower()}.eval.json").read_text(encoding="utf-8"))
    assert any(call["agent"] == "judge_second_pass" for call in model.calls)
    assert not any(trigger.trigger == "stability_disagreement" for trigger in case.ruling.review_triggers)
    if dispute_id == "DISP-010":
        assert case.status == "pending_review" and case.ruling.amount is None
    else:
        assert case.ruling.status == "final" and case.ruling.outcome == expected["expected_outcome"]
        assert case.ruling.amount == (Decimal(expected["expected_amount"]) if "expected_amount" in expected else None)


@pytest.mark.parametrize("dispute_id", ["DISP-008", "DISP-009", "DISP-010"])
def test_recorded_route_outcomes_and_raw_inputs_match_for_every_switch_combination(dispute_id):
    directory = Path(__file__).resolve().parents[1] / "src/api/static/recorded"
    paths = [directory / f"{dispute_id}.json", *directory.glob(f"{dispute_id}.*.json")]
    assert len(paths) == 16
    expected = json.loads((DEFAULT_DATA_DIR / f"{dispute_id.lower()}.eval.json").read_text(encoding="utf-8"))
    for path in paths:
        case = json.loads(path.read_text(encoding="utf-8"))["case"]
        ruling = case["ruling"]
        if dispute_id == "DISP-010":
            assert case["status"] == "pending_review" and ruling["amount"] is None, path.name
        else:
            assert ruling["status"] == "final" and ruling["outcome"] == expected["expected_outcome"], path.name
            assert ruling["amount"] == expected.get("expected_amount"), path.name
        route = next(item for item in case["evidence"] if item["source"] == "route")
        assert route["content"]["trip"]["trip_id"] == case["dispute"]["trip_id"], path.name


def test_partial_refund_is_recomputed_from_receipt_and_tariff_and_shows_its_work():
    case = run("DISP-008")
    assert case.ruling.outcome == "partially_uphold" and case.ruling.status == "final"
    assert case.ruling.amount == Decimal("5.39")
    assert case.ruling.amount < Decimal(record()["receipt"]["paid_net"])
    calculation = case.ruling.calculation
    assert set(calculation.input_evidence_ids) == {"EV-ROUTE-1", "EV-FARE-1"}
    for value in ["ADR 0004", "optimal_net=max", "refund=min", "surge=1.20", "promo=2.00", "paid_net=", "optimal_km=", "half-up"]:
        assert value in calculation.formula
    next(item for item in case.evidence if item.source == "fare").derived["refund"] = "999.00"
    assert amount_for(case, Remedy.PARTIAL_REFUND, calculation.input_evidence_ids)[0] == Decimal("5.39")
    assert all("no-show" not in outcome.ruling_summary for outcome in case.outcomes)


def test_consent_cites_exact_request_and_ambiguity_authorises_no_amount():
    case = run("DISP-009")
    request = next(message for message in record_for("DISP-009")["chat_logs"] if message["id"] == "MSG-009-1")
    driver = next(sub for sub in case.submissions if sub.author == "driver_advocate")
    assert request["content"] in driver.claim_restated and request["id"] in driver.claim_restated
    assert "EV-CHAT-1" in driver.facts_relied_on
    assert case.ruling.outcome == "reject" and case.ruling.amount is None
    pending = run("DISP-010")
    assert pending.status == "pending_review" and pending.ruling.status == "proposal"
    assert pending.ruling.balance_of_evidence == "balanced"
    assert pending.ruling.amount is None and pending.ruling.calculation is None
    assert all(outcome.action_status == "pending_review" for outcome in pending.outcomes)


def record_for(dispute_id):
    catalog = load_catalog()
    return catalog.trip(catalog.dispute(dispute_id).trip_id)


@pytest.mark.parametrize("baseline", [None, [], "invalid", {}, {"points": []}])
def test_malformed_or_missing_baseline_is_explicitly_unavailable(baseline):
    raw = record()
    raw["route_baseline"] = baseline
    result = analyze_route(raw)
    assert result["available"] is False and result["unavailable_reason"]
    assert analyze_fare(raw, result)["available"] is False


@pytest.mark.parametrize("field,value", [("surge", None), ("surge", "0"), ("promo", None), ("km_rate", "NaN"), ("base", "-1"), ("minute_rate", True)])
def test_invalid_or_missing_pricing_never_guesses_a_refund(field, value):
    raw = record()
    if value is None:
        del raw["tariff"][field]
    else:
        raw["tariff"][field] = value
    result = analyze_fare(raw, analyze_route(raw))
    assert result["available"] is False and "refund" not in result


@pytest.mark.parametrize("field", ["tariff", "receipt", "gps_telemetry", "chat_logs"])
def test_absent_material_sources_produce_missing_evidence_and_review(field):
    catalog = load_catalog()
    raw = record()
    raw.pop(field)
    changed = Catalog(disputes=catalog.disputes, trips={**catalog.trips, raw["trip"]["trip_id"]: raw})
    items = gather_evidence(raw["trip"]["trip_id"], changed)
    missing_source = "chat" if field == "chat_logs" else "fare"
    assert next(item for item in items if item.source == missing_source).status == "missing"
    case = run("DISP-008", catalog=changed)
    assert case.status == "pending_review"
    assert case.ruling is None or case.ruling.amount is None


def test_unreconciled_receipt_and_invalid_coordinates_are_unavailable():
    raw = record()
    raw["receipt"]["paid_net"] = "99.00"
    assert analyze_fare(raw, analyze_route(raw))["available"] is False
    raw["gps_telemetry"][2]["lat"] = float("nan")
    assert analyze_route(raw)["available"] is False


def test_endpoints_jitter_and_gaps_never_invent_stops_or_a_complete_path():
    raw = record()
    original = raw["gps_telemetry"]
    raw["gps_telemetry"] = [original[0], original[-1]]
    assert "Insufficient path" in analyze_route(raw)["unavailable_reason"]
    raw["gps_telemetry"] = original
    raw["gps_telemetry"][7]["gap_before"] = True
    analysis = analyze_route(raw)
    assert analysis["available"] is False and analysis["telemetry_gaps"] == 1
    assert not analysis["stop_candidates"]
    # Stationary jitter at an interior stop remains a bounded observed interval.
    raw = record()
    raw["gps_telemetry"][6]["lat"] += .00001
    assert analyze_route(raw)["stop_candidates"][0]["observed_seconds"] == 180
    endpoint = deepcopy(raw["gps_telemetry"][:4])
    for point in endpoint:
        point.update(lat=endpoint[0]["lat"], lng=endpoint[0]["lng"])
    assert stop_candidates(endpoint) == []


def test_stop_cluster_touching_endpoint_exclusion_is_not_an_unexpected_stop():
    points = [
        {"lat": 0, "lng": distance / 111195, "timestamp": f"2026-09-16T14:0{minute}:00+08:00"}
        for minute, distance in enumerate((0, 60, 55, 45, 200))
    ]
    # The cluster starts beyond 50 m but finishes inside the pickup exclusion.
    assert stop_candidates(points) == []


def test_half_up_zero_and_capped_refunds_and_no_missing_promo_default():
    raw = record()
    raw["tariff"] = {"base": "0", "km_rate": "0", "minute_rate": "0.00025", "surge": "1", "booking": "0", "tolls": "0", "promo": "0"}
    raw["receipt"]["paid_net"] = "0.01"
    assert analyze_fare(raw, analyze_route(raw))["refund"] == "0.01"  # 0.007 -> 0.01
    raw["tariff"]["promo"] = "100"
    raw["receipt"]["paid_net"] = "0.00"
    assert analyze_fare(raw, analyze_route(raw))["refund"] == "0.00"


def test_four_clauses_and_partial_burden_and_monetary_inputs_are_enforced():
    assert [clause.clause_id for clause in policy_for(DisputeCategory.ROUTE_DEVIATION)] == ["R-04", "D-04", "R-03", "D-03"]
    case = run("DISP-008")
    args = arguments_in(*case.submissions)
    draft = JudgeDraft.model_validate(stub_replies("DISP-008")["judge"])
    assert draft_problems(case, args, draft) == []
    draft.balance_of_evidence = BalanceOfEvidence.BALANCED
    assert draft_problems(case, args, JudgeDraft.model_validate(draft.model_dump()))
    draft = JudgeDraft.model_validate(stub_replies("DISP-008")["judge"])
    draft.amount_input_evidence_ids = ["EV-FARE-1"]
    assert any("both EV-ROUTE-1" in problem for problem in draft_problems(case, args, draft))
    assert '"vehicle_gps":' not in evidence_for_prompt(case)


def test_route_is_bound_to_booked_endpoints_and_complete_trip_times():
    raw = record()
    raw["trip"]["pickup_location"]["lat"] = 1.5
    assert not analyze_route(raw)["available"]
    raw = record()
    raw["trip"]["completed_at"] = "2026-09-16T14:21:00+08:00"
    assert not analyze_route(raw)["available"]


@pytest.mark.parametrize("field,value", [("receipt_id", ""), ("trip_id", "WRONG"), ("timestamp", "2026-09-16T14:10:00+08:00")])
def test_receipt_needs_identity_trip_association_and_completion_time(field, value):
    raw = record()
    raw["receipt"][field] = value
    assert not analyze_fare(raw, analyze_route(raw))["available"]


def test_extreme_finite_pricing_is_unavailable_instead_of_overflowing():
    raw = record()
    raw["tariff"]["surge"] = "1e999999"
    assert not analyze_fare(raw, analyze_route(raw))["available"]


def test_a_monetary_route_proposal_has_no_authorised_amount():
    store = CaseStore()
    script = stub_replies("DISP-008")
    script["judge"].update(policy_fit="unclear", policy_gap="No clause resolves an unverified fare adjustment.")
    case = run("DISP-008", store, ReplayModel(store, {"DISP-008": script}))
    assert case.status == "pending_review" and case.ruling.remedy == "partial_refund"
    assert case.ruling.amount is case.ruling.currency is case.ruling.calculation is None


def test_route_money_is_also_suppressed_after_a_history_review_trigger(monkeypatch):
    from src.config import HistoryRule
    from src.agents.judge.history import apply_history
    import src.orchestrator as orchestrator
    rules = (HistoryRule(key="prior_rejected", description="Review history signal", lowers_confidence=False, triggers_review=True),)
    monkeypatch.setattr(orchestrator, "apply_history", lambda ruling, case: apply_history(ruling, case, rules))
    catalog = load_catalog()
    raw = record()
    raw["rider_history"]["dispute_history"]["rejected"] = 3
    changed = Catalog(disputes=catalog.disputes, trips={**catalog.trips, raw["trip"]["trip_id"]: raw})
    case = run("DISP-008", catalog=changed)
    assert case.status == "pending_review" and case.ruling.outcome == "partially_uphold"
    assert case.ruling.amount is case.ruling.currency is case.ruling.calculation is None


def test_route_proposal_from_late_amount_limit_clears_money(monkeypatch):
    from src.config import CONFIG
    monkeypatch.setattr("src.agents.escalation.CONFIG", CONFIG.model_copy(update={"escalation": CONFIG.escalation.model_copy(update={"amount_limit": Decimal("1")})}))
    case = run("DISP-008")
    assert case.status == "pending_review"
    assert case.ruling.amount is case.ruling.currency is case.ruling.calculation is None


def test_route_human_confirm_recomputes_suppressed_partial_refund(monkeypatch):
    from src.config import CONFIG
    from src.agents.escalation import decide_review
    from src.contracts import ReviewDecision
    monkeypatch.setattr("src.agents.escalation.CONFIG", CONFIG.model_copy(update={"escalation": CONFIG.escalation.model_copy(update={"amount_limit": Decimal("1")})}))
    store = CaseStore()
    case = run("DISP-008", store)
    decided = decide_review(store, case.case_id, reviewer="Demo reviewer", decision=ReviewDecision.CONFIRM)
    assert decided.ruling.amount == Decimal("5.39")
    assert decided.ruling.calculation.result == decided.ruling.amount
    assert set(decided.ruling.calculation.input_evidence_ids) == {"EV-ROUTE-1", "EV-FARE-1"}
    assert decided.status == "notified"


def test_route_human_override_reject_to_partial_and_partial_to_reject(monkeypatch):
    from src.config import CONFIG
    from src.agents.escalation import decide_review
    from src.contracts import ReviewDecision
    store = CaseStore()
    case = run("DISP-010", store)
    decided = decide_review(store, case.case_id, reviewer="Demo reviewer", decision=ReviewDecision.OVERRIDE, reason="Reviewed the disputed route.")
    assert decided.ruling.outcome == "partially_uphold" and decided.ruling.remedy == "partial_refund"
    assert decided.ruling.amount == Decimal("5.39")
    assert set(decided.ruling.calculation.input_evidence_ids) == {"EV-ROUTE-1", "EV-FARE-1"}
    monkeypatch.setattr("src.agents.escalation.CONFIG", CONFIG.model_copy(update={"escalation": CONFIG.escalation.model_copy(update={"amount_limit": Decimal("1")})}))
    store = CaseStore(); case = run("DISP-008", store)
    decided = decide_review(store, case.case_id, reviewer="Demo reviewer", decision=ReviewDecision.OVERRIDE, reason="Reviewed contrary evidence.")
    assert decided.ruling.outcome == "reject" and decided.ruling.remedy == "no_action"
    assert decided.ruling.amount is decided.ruling.calculation is None


def test_route_review_refuses_unavailable_inputs_without_mutation():
    from src.agents.escalation import decide_review, ReviewInvalid
    from src.contracts import ReviewDecision, EvidenceStatus
    store = CaseStore(); case = run("DISP-010", store)
    case.evidence[0].status = EvidenceStatus.MISSING
    # CaseStore owns this snapshot; use its existing mutable case for the failure seam.
    store._cases[case.case_id] = case
    with pytest.raises(ReviewInvalid, match="available"):
        decide_review(store, case.case_id, reviewer="Demo reviewer", decision=ReviewDecision.OVERRIDE, reason="Cannot assume missing telemetry.")
    assert store.get_case(case.case_id).status == "pending_review"


def test_route_fixture_conversation_matches_trip_chronology():
    catalog = load_catalog()
    consent = catalog.trip("TRIP-2026-ROUTE-009")
    assert consent["chat_logs"][-1]["timestamp"] < consent["trip"]["started_at"]
    admission = record()
    assert admission["chat_logs"][1]["timestamp"] > admission["gps_telemetry"][8]["timestamp"]


def test_escalation_disabled_preserves_recomputed_route_money():
    from src.contracts import Switches
    store = CaseStore(); catalog = load_catalog()
    script = stub_replies("DISP-008")
    script["judge"].update(policy_fit="unclear", policy_gap="Unverified fare adjustment.")
    case = run_dispute(catalog.dispute("DISP-008"), store=store, model=ReplayModel(store, {"DISP-008": script}), catalog=catalog, switches=Switches(escalation=False))
    assert case.ruling.status == "final" and case.ruling.amount == Decimal("5.39")
    assert all("SGD 5.39" in outcome.ruling_summary for outcome in case.outcomes)


def test_recomputing_refund_ignores_tampered_derived_route_metrics():
    case = run("DISP-008")
    route = next(item for item in case.evidence if item.source == "route")
    route.derived["optimal_km"] = "1.000"
    amount, _ = amount_for(case, Remedy.PARTIAL_REFUND, ["EV-ROUTE-1", "EV-FARE-1"])
    assert amount == Decimal("5.39")


def test_empty_conversation_is_missing_and_held_for_review():
    catalog = load_catalog(); raw = deepcopy(catalog.trip("TRIP-2026-ROUTE-009")); raw["chat_logs"] = []
    changed = Catalog(disputes=catalog.disputes, trips={**catalog.trips, raw["trip"]["trip_id"]: raw})
    case = run("DISP-009", catalog=changed)
    assert next(item for item in case.evidence if item.source == "chat").status == "missing"
    assert case.status == "pending_review"
    assert case.ruling is None or case.ruling.amount is None


def test_full_refund_review_classification_and_amount():
    from src.agents.escalation import decide_review
    from src.contracts import ReviewDecision
    store = CaseStore(); case = run("DISP-010", store)
    fare = next(item for item in case.evidence if item.source == "fare")
    fare.content["tariff"] = {"base": "0", "km_rate": "0", "minute_rate": "0.00025", "surge": "1", "booking": "0", "tolls": "0", "promo": "0"}
    fare.content["receipt"]["paid_net"] = "0.01"
    store._cases[case.case_id] = case
    final = decide_review(store, case.case_id, reviewer="Demo reviewer", decision=ReviewDecision.OVERRIDE, reason="Reviewed all source records.")
    assert final.ruling.outcome == "uphold" and final.ruling.remedy == "full_refund"
    assert final.ruling.amount == final.ruling.calculation.result == Decimal("0.01")


@pytest.mark.parametrize("dispute_id,text", [("DISP-008", "partially upheld"), ("DISP-009", "No refund is recommended")])
def test_both_route_outcomes_match_ruling(dispute_id, text):
    case = run(dispute_id)
    assert len(case.outcomes) == 2
    assert all(text in outcome.ruling_summary and outcome.action_status == "recommended" for outcome in case.outcomes)
    if case.ruling.amount:
        assert all(f"SGD {case.ruling.amount}" in outcome.ruling_summary for outcome in case.outcomes)
