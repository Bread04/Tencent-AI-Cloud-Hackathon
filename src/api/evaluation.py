"""The evaluation page and its API (ticket 20): run every mock case and show the table, the pass rate and which model made it."""

import threading
from collections.abc import Callable
from html import escape
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from src.config import CONFIG
from src.evaluation import evaluate
from src.intake import Catalog
from src.llm.adapter import ModelAdapter
from src.store import CaseStore

HERE = Path(__file__).resolve().parent


def add_evaluation_routes(
    app: FastAPI, *, catalog: Catalog, model_for: Callable[[CaseStore], ModelAdapter], simulated: str, model_label: str
) -> None:
    state: dict = {"state": "none"}  # none, running, done or failed; the latest report stays until the next run
    lock = threading.Lock()

    @app.get("/evaluation", response_class=HTMLResponse)
    def evaluation_page():
        page = (HERE / "evaluation.html").read_text(encoding="utf-8")
        return page.replace("{{SIMULATED}}", escape(simulated)).replace("{{MODEL_LABEL}}", escape(model_label))

    @app.get("/api/evaluation")
    def latest():
        return state

    @app.post("/api/evaluation/run", status_code=202)
    def run():
        """Start a run in the background (a live model takes minutes) and return at once; the page polls `/api/evaluation`."""
        with lock:
            if state["state"] == "running":
                return JSONResponse({"error": "An evaluation is already running."}, status_code=409)
            state.update(state="running", error=None)

        def work():
            try:
                # Safety Incidents are only resolvable with SLA routing, so the evaluation turns it on.
                switches = CONFIG.switches.model_copy(update={"sla_routing": True})
                report = evaluate(catalog=catalog, model_for=model_for, switches=switches, model_label=model_label)
                state.update(state="done", report=report.as_json())
            except Exception as error:  # shown on the page, never hidden
                state.update(state="failed", error=f"{type(error).__name__}: {error}")

        threading.Thread(target=work, daemon=True).start()
        return {"state": "running"}
