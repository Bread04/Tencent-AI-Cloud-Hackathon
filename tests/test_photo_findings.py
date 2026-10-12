"""Seam: Image Analysis (ticket 14, architecture 5.4). A photo becomes evidence with stated uncertainty; signals, never proof."""

import json
from datetime import datetime

from src.agents.image_analysis import analyse_photos
from src.contracts import CaseStatus, EvidenceStatus, LogEventKind, Switches
from src.intake import load_catalog
from src.llm import ModelError, StubModel
from src.orchestrator import run_dispute
from src.store import CaseStore
from src.tools.photos import capture_time, timestamp_alignment

GENUINE, OLD, SYNTHETIC = "data/photos/seat-stain.png", "data/photos/seat-stain-old.png", "data/photos/seat-stain-synthetic.png"
WINDOW = (datetime.fromisoformat("2026-09-14T10:00:00+08:00"), datetime.fromisoformat("2026-09-14T10:04:00+08:00"))
ON = Switches(image_analysis=True, escalation=True)


def reading(description="A dark stain on a rear seat.", signal="none", confidence=0.8, uncertainty="Low light; the stain could be a shadow."):
    return {"description": description, "ai_generation_signal": signal, "confidence": confidence, "uncertainty": uncertainty}


def a_case(photos):
    catalog, store = load_catalog(), CaseStore()
    dispute = catalog.dispute("DISP-003").model_copy(update={"photos": photos})
    return store.get_case(store.create_case(dispute, ON).case_id), catalog


def analyse(photos, reply, window=WINDOW):
    case, _ = a_case(photos)
    model = StubModel({(case.case_id, "image_analysis"): reply})
    return model, analyse_photos(case, window, model)


# --- Timestamp alignment is code ---------------------------------------------------------------------------------------------------------


def test_a_photo_taken_inside_the_trip_window_is_aligned():
    assert capture_time(GENUINE) == datetime.fromisoformat("2026-09-14T10:02:00+08:00")
    assert timestamp_alignment(capture_time(GENUINE), *WINDOW).state == "aligned"


def test_a_photo_from_a_different_date_is_outside_the_window():
    result = timestamp_alignment(capture_time(OLD), *WINDOW)

    assert result.state == "outside_window" and "2026-08" in result.detail


def test_a_photo_with_no_metadata_is_unknown_not_guessed():
    assert capture_time("data/photos/does-not-exist.png") is None
    result = timestamp_alignment(None, *WINDOW)

    assert result.state == "unknown" and "no capture time" in result.detail


# --- Three findings, each with its uncertainty ---------------------------------------------------------------------------------------


def test_a_photo_produces_a_description_a_timestamp_and_an_ai_generation_finding_each_with_uncertainty():
    _, items = analyse([GENUINE], reading())

    assert [i.evidence_id for i in items] == ["EV-PHOTO-1-DESC", "EV-PHOTO-1-TIME", "EV-PHOTO-1-AI"]
    assert {i.source for i in items} == {"photo_finding"} and {i.status for i in items} == {EvidenceStatus.AVAILABLE}
    assert items[0].content == "A dark stain on a rear seat."
    assert items[1].derived["alignment"] == "aligned" and items[2].derived["signal"] == "none"
    assert all(i.derived["uncertainty"] for i in items)
    assert items[2].derived["confidence"] == 0.8


def test_the_photo_is_sent_to_the_model_as_an_image_and_its_text_is_treated_as_untrusted():
    model, _ = analyse([GENUINE], reading())

    call = model.calls[0]
    assert call["images"] and call["images"][0].endswith("seat-stain.png")
    assert "untrusted" in json.dumps(call["messages"]) and "signal" in json.dumps(call["messages"])


def test_a_photo_from_another_date_gets_an_outside_window_finding_whatever_the_model_says():
    _, items = analyse([OLD], reading())

    assert items[1].derived["alignment"] == "outside_window"


def test_a_photo_that_looks_generated_is_reported_as_a_signal_not_a_verdict():
    _, items = analyse([SYNTHETIC], reading(signal="likely", confidence=0.7))

    ai = items[2]
    assert ai.derived["signal"] == "likely" and "signal" in ai.content and "not proof" in ai.content


def test_an_uncertainty_that_is_left_blank_is_sent_back():
    case, _ = a_case([GENUINE])
    model = StubModel({(case.case_id, "image_analysis"): [reading(uncertainty=" "), reading()]})

    items = analyse_photos(case, WINDOW, model)

    assert items[0].status is EvidenceStatus.AVAILABLE and len(model.calls) == 2


def test_more_than_one_photo_gets_its_own_numbered_findings():
    _, items = analyse([GENUINE, OLD], reading())

    assert [i.evidence_id for i in items][3:] == ["EV-PHOTO-2-DESC", "EV-PHOTO-2-TIME", "EV-PHOTO-2-AI"]


# --- The image model is unavailable ----------------------------------------------------------------------------------------------------


def test_with_the_image_model_unavailable_the_photo_is_recorded_as_unanalysed_with_the_cause():
    case, _ = a_case([GENUINE])

    class Dead:
        def complete(self, messages, *, case_id, agent, schema=None, images=None):
            raise ModelError("The model timed out after 120 seconds (agent image_analysis).")

    (item,) = analyse_photos(case, WINDOW, Dead())

    assert item.evidence_id == "EV-PHOTO-1" and item.status is EvidenceStatus.MISSING
    assert "unanalysed" in item.content and "timed out" in item.content


# --- In a whole run --------------------------------------------------------------------------------------------------------------------


def run(switches, photos=(GENUINE,)):
    from src.api.demo import ReplayModel

    catalog, store = load_catalog(), CaseStore()
    dispute = catalog.dispute("DISP-003").model_copy(update={"photos": list(photos)})
    model = ReplayModel(store)
    case = run_dispute(dispute, store=store, model=model, catalog=catalog, switches=switches)
    return store, case, model


def test_with_the_switch_on_findings_are_sealed_with_the_evidence_and_each_photo_is_logged():
    store, case, _ = run(ON)

    assert {"EV-PHOTO-1-DESC", "EV-PHOTO-1-TIME", "EV-PHOTO-1-AI"} <= {i.evidence_id for i in case.evidence}
    logged = [e for e in store.log(case.case_id) if e.kind is LogEventKind.PHOTO_ANALYSED]
    assert len(logged) == 1 and "seat-stain.png" in logged[0].summary
    assert case.status is CaseStatus.NOTIFIED


def test_with_the_switch_off_photos_are_stored_but_not_analysed():
    store, case, model = run(Switches(escalation=True))

    assert case.dispute.photos == [GENUINE]
    assert not [i for i in case.evidence if i.source == "photo_finding"]
    assert not [c for c in model.calls if c["agent"] == "image_analysis"]
    assert not [e for e in store.log(case.case_id) if e.kind is LogEventKind.PHOTO_ANALYSED]


def test_a_failed_image_model_does_not_stop_the_case():
    from src.api.demo import ReplayModel

    catalog, store = load_catalog(), CaseStore()
    dispute = catalog.dispute("DISP-003").model_copy(update={"photos": [GENUINE]})
    model = ReplayModel(store, scripts={"DISP-003": {k: v for k, v in __import__("src.llm.stub", fromlist=["x"]).load_replies("DISP-003").items() if k != "image_analysis"}})

    case = run_dispute(dispute, store=store, model=model, catalog=catalog, switches=ON)

    assert any(i.evidence_id == "EV-PHOTO-1" and i.status is EvidenceStatus.MISSING for i in case.evidence)
    assert case.ruling is not None
