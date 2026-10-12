"""The Demo Day console and the pages behind it.

`/` is the console (`console.html` plus `static/`): pick a prepared Dispute, run it, and watch the
Communication Log, the Ruling and both Outcomes fill in. It reads the JSON API (`/api/...`).
`/cases/{id}` is the plain server-rendered Case page. Everything shown is Mock Data and says so.
"""

import threading
import time
from html import escape
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.agents.policy import SIMULATED_LABEL as POLICY_SIMULATED
from src.config import CONFIG
from src.contracts import Case, LogEvent
from src.intake import Catalog, UnknownDispute
from src.llm.adapter import ModelAdapter
from src.orchestrator import run_dispute
from src.store import CaseNotFound, CaseStore

SIMULATED = "Simulated: all trips, evidence, policy and payments on this page are mock data."
HERE = Path(__file__).resolve().parent
PROTOTYPES = HERE.parents[1] / "prototypes"
START_TIMEOUT_SECONDS = 5  # how long a run may take to create its Case before the start request gives up


def create_app(*, store: CaseStore, model: ModelAdapter, catalog: Catalog) -> FastAPI:
    app = FastAPI(title="Ryde Dispute Resolution (simulated)")
    run_errors: dict[str, str] = {}  # case id -> why its run stopped, for the console
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    # The console uses the Waypoint prototype's own stylesheets, fonts and artwork, so it looks like the rider app.
    app.mount("/prototypes", StaticFiles(directory=PROTOTYPES), name="prototypes")

    @app.get("/", response_class=HTMLResponse)
    def home():
        rows = "".join(_dispute_row(d, catalog.trip(d.trip_id)["trip"]) for d in catalog.disputes.values())
        template = (HERE / "console.html").read_text(encoding="utf-8")
        return template.replace("{{SIMULATED}}", escape(SIMULATED)).replace("{{DISPUTES}}", rows).replace("{{COUNT}}", str(len(catalog.disputes))).replace("{{THRESHOLD}}", str(CONFIG.escalation.confidence_threshold))

    @app.post("/api/disputes/{dispute_id}/run", status_code=202)
    def start_run(dispute_id: str):
        """Start a run in the background and return its Case ID as soon as the Case exists, so the console can watch it."""
        try:
            dispute = catalog.dispute(dispute_id)
        except UnknownDispute as error:
            return JSONResponse({"error": str(error)}, status_code=404)
        known = {case.case_id for case in store.list_cases()}

        def work():
            try:
                run_dispute(dispute, store=store, model=model, catalog=catalog)
            except Exception as error:  # a failed run is shown in the console, never hidden
                created = [case.case_id for case in store.list_cases() if case.case_id not in known]
                if created:
                    run_errors[created[0]] = f"{type(error).__name__}: {error}"

        threading.Thread(target=work, daemon=True).start()
        deadline = time.monotonic() + START_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            created = [case.case_id for case in store.list_cases() if case.case_id not in known]
            if created:
                return {"case_id": created[0]}
            time.sleep(0.01)
        return JSONResponse({"error": f"The run for {dispute_id} did not start."}, status_code=504)

    @app.get("/api/cases/{case_id}")
    def case_json(case_id: str):
        try:
            case, log = store.get_case(case_id), store.log(case_id)
        except CaseNotFound as error:
            return JSONResponse({"error": str(error)}, status_code=404)
        return {
            "case": case.model_dump(mode="json"),
            "log": [event.model_dump(mode="json") for event in log],
            "run_error": run_errors.get(case_id),
        }

    @app.post("/disputes/{dispute_id}/run")
    def run(dispute_id: str):
        try:
            dispute = catalog.dispute(dispute_id)
        except UnknownDispute as error:
            return HTMLResponse(_page("Not found", f"<p>{escape(str(error))}</p>"), status_code=404)
        case = run_dispute(dispute, store=store, model=model, catalog=catalog)
        return RedirectResponse(f"/cases/{case.case_id}", status_code=303)

    @app.get("/cases/{case_id}", response_class=HTMLResponse)
    def show_case(case_id: str):
        try:
            case, log = store.get_case(case_id), store.log(case_id)
        except CaseNotFound as error:
            return HTMLResponse(_page("Not found", f"<p>{escape(str(error))}</p>"), status_code=404)
        return _page(f"Case {case_id}", _ruling_html(case) + _policy_html(case) + _log_html(log))

    return app


def _dispute_row(dispute, trip: dict) -> str:
    """One Dispute in the picker, in the rider app's trip-choice style. The data attributes fill the trip panel."""
    pickup, dropoff = trip["pickup_location"]["name"], trip["dropoff_location"]["name"]
    fee = f"{trip['currency']} {trip['cancellation_fee']}"
    when = trip["scheduled_time"][:16].replace("T", " ")
    return (
        f"<button type='button' class='trip-choice' aria-pressed='false' data-dispute='{escape(dispute.dispute_id)}' "
        f"data-category='{escape(dispute.category.value)}' data-pickup='{escape(pickup)}' data-destination='{escape(dropoff)}' "
        f"data-fare='{escape(fee)}' data-when='{escape(when)}' data-filed-by='{escape(dispute.filed_by.value)}' "
        f"data-description='{escape(dispute.description)}'>"
        f"<span class='row'><strong>{escape(dispute.dispute_id)}</strong>"
        f"<span class='tag'>{escape(dispute.category.value.replace('_', ' '))}</span></span>"
        f"<span class='journey'>{escape(pickup)}<small>→ {escape(dropoff)}</small></span>"
        f"<span class='small muted'>{escape(when)} SGT · {escape(fee)} fee</span></button>"
    )


def _page(title: str, body: str) -> str:
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>{escape(title)}</title>"
        "<link rel='stylesheet' href='/static/console.css'></head><body class='plain'>"
        f"<p><strong>{SIMULATED}</strong></p><h1>{escape(title)}</h1>{body}"
        "<p><a href='/'>Prepared Disputes</a></p></body></html>"
    )


def _ruling_html(case: Case) -> str:
    ruling = case.ruling
    if ruling is None:
        return f"<h2>Ruling</h2><p>No Ruling. Case status: {escape(case.status.value)}.</p>"
    amount = f"{escape(ruling.currency)} {ruling.amount}" if ruling.amount is not None else "none"
    components = ", ".join(f"{escape(name)} {value}" for name, value in ruling.confidence.components.items())
    return (
        "<h2>Ruling</h2><ul>"
        f"<li>Outcome: {escape(ruling.outcome.value)} (remedy: {escape(ruling.remedy.value)})</li>"
        f"<li>Amount: {amount}</li>"
        f"<li>Confidence: {ruling.confidence.value} ({components})</li>"
        f"<li>Reasoning: {escape(ruling.reasoning_summary)}</li></ul>"
    )


def _log_html(log: list[LogEvent]) -> str:
    rows = "".join(
        f"<li>{escape(e.timestamp.isoformat())} · {escape(e.agent)} · {escape(e.kind.value)}: {escape(e.summary)}</li>"
        for e in log
    )
    return f"<h2>Communication Log</h2><ol>{rows}</ol>"


def _policy_html(case: Case) -> str:
    if not case.policy_clauses:
        return ""
    rows = "".join(
        f"<li><strong>{escape(c.clause_id)}</strong> (version {escape(c.version)}): {escape(c.text)}</li>"
        for c in case.policy_clauses
    )
    return f"<h2>Policy</h2><p>{escape(POLICY_SIMULATED)}</p><ul>{rows}</ul>"
