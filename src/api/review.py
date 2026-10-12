"""The reviewer's side of the API (ticket 09): the queue of held Cases, a Case's review package, and the decision."""

from html import escape
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from src.agents.escalation import ReviewInvalid, ReviewNotPossible, decide_review, review_package
from src.contracts import CaseStatus, ReviewDecision
from src.store import CaseNotFound, CaseStore

HERE = Path(__file__).resolve().parent


class DecisionRequest(BaseModel):
    reviewer: str
    decision: ReviewDecision
    reason: str | None = None


def add_review_routes(app: FastAPI, *, store: CaseStore, simulated: str, model_label: str) -> None:
    @app.get("/review", response_class=HTMLResponse)
    def review_screen():
        page = (HERE / "review.html").read_text(encoding="utf-8")
        return page.replace("{{SIMULATED}}", escape(simulated)).replace("{{MODEL_LABEL}}", escape(model_label))

    @app.get("/api/review")
    def queue():
        held = [case for case in store.list_cases() if case.status is CaseStatus.PENDING_REVIEW]
        return {
            "cases": [
                {
                    "case_id": case.case_id,
                    "dispute_id": case.dispute.dispute_id,
                    "category": case.dispute.category.value,
                    "status": case.status.value,
                    "proposed_outcome": case.ruling.outcome.value if case.ruling else None,
                    "confidence": case.ruling.confidence.value if case.ruling and case.ruling.confidence else None,
                    "reasons": [r.model_dump(mode="json") for r in review_package(case, store.log(case.case_id)).reasons],
                    "updated_at": case.updated_at.isoformat(),
                }
                for case in held
            ]
        }

    @app.get("/api/review/{case_id}")
    def package(case_id: str):
        try:
            case, log = store.get_case(case_id), store.log(case_id)
        except CaseNotFound as error:
            return JSONResponse({"error": str(error)}, status_code=404)
        return review_package(case, log).model_dump(mode="json") | {"status": case.status.value, "review_record": case.review_record.model_dump(mode="json") if case.review_record else None}

    @app.post("/api/review/{case_id}/decision")
    def decide(case_id: str, request: DecisionRequest):
        try:
            case = decide_review(store, case_id, reviewer=request.reviewer, decision=request.decision, reason=request.reason)
        except CaseNotFound as error:
            return JSONResponse({"error": str(error)}, status_code=404)
        except ReviewNotPossible as error:
            return JSONResponse({"error": str(error)}, status_code=409)
        except ReviewInvalid as error:
            return JSONResponse({"error": str(error)}, status_code=422)
        return {"case": case.model_dump(mode="json"), "log": [e.model_dump(mode="json") for e in store.log(case_id)]}
