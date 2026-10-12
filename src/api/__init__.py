"""The Demo Day console and the pages behind it.

`/` is the console (`console.html` plus `static/`): pick a prepared Dispute, run it, and watch the
Communication Log, the Ruling and both Outcomes fill in. It reads the JSON API (`/api/...`).
`/cases/{id}` is the plain server-rendered Case page. Everything shown is Mock Data and says so.
"""

import threading
from collections.abc import Callable
import time
from html import escape
import json
import os
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agents.policy import SIMULATED_LABEL as POLICY_SIMULATED
from src.agents.intake import IntakeError, resolve_category
from src.api.demo_switches import checkboxes_html, switches_from_query
from src.api.evaluation import add_evaluation_routes
from src.api.review import add_review_routes
from src.config import CONFIG
from src.api.chat import (CHAT_STYLE, COOKIE_NAME, SESSION_SECONDS, CLIENT_COOKIE_NAME,
                         TRANSCRIPT_SECONDS, MAX_TRANSCRIPT_BYTES, ChatAccess, RiderTranscripts,
                         validate_rider_transcript, case_path, locked_html, log_html)
from src.api.rider import install_rider_routes
from src.contracts import Case, DisputeCategory, LogEvent, RulingStatus
from src.intake import Catalog, UnknownDispute
from src.llm.adapter import ModelAdapter
from src.orchestrator import run_dispute
from src.store import CaseNotFound, CaseStore

SIMULATED = "Simulated: all trips, evidence, policy and payments on this page are mock data."
HERE = Path(__file__).resolve().parent
PROTOTYPES = HERE.parents[1] / "prototypes"
START_TIMEOUT_SECONDS = 5  # how long a run may take to create its Case before the start request gives up


class ClassifyRequest(BaseModel):
    description: str
    category: str | None = None


def create_app(
    *,
    store: CaseStore,
    model: ModelAdapter,
    catalog: Catalog,
    model_label: str = "Scripted replies",
    model_for: Callable[[CaseStore], ModelAdapter] | None = None,
) -> FastAPI:
    app = FastAPI(title="Ryde Dispute Resolution (simulated)")
    run_errors: dict[str, str] = {}  # case id -> why its run stopped, for the console
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    # The console uses the Waypoint prototype's own stylesheets, fonts and artwork, so it looks like the rider app.
    app.mount("/prototypes", StaticFiles(directory=PROTOTYPES), name="prototypes")
    access = ChatAccess(os.environ.get("RYDE_CHAT_ACCESS_CODE", "482731"))
    app.state.chat_access = access
    transcripts = RiderTranscripts()
    app.state.rider_transcripts = transcripts
    install_rider_routes(app, transcripts)

    @app.middleware("http")
    async def prevent_case_caching(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/cases/", "/api/rider-chat/", "/api/rider/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    def set_session(response, request, token):
        response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="strict", max_age=SESSION_SECONDS,
                            secure=request.url.scheme == "https")

    async def bounded_json(request, limit):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > limit:
                return None
        try:
            return json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, RecursionError):
            return None

    def owned_transcript(handle, request, *, metadata_only=True):
        try:
            return transcripts.get(handle, request.cookies.get(CLIENT_COOKIE_NAME), metadata_only=metadata_only)
        except KeyError:
            return JSONResponse({"error": "Communication Log unavailable or expired. Explicitly prepare the Rider case again."}, status_code=404)
        except PermissionError:
            return JSONResponse({"error": "Communication Log belongs to another browser session. Prepare this Rider case again."}, status_code=403)

    @app.post("/api/rider-chat/transcripts")
    async def register_rider_transcript(request: Request):
        payload = await bounded_json(request, MAX_TRANSCRIPT_BYTES)
        if not validate_rider_transcript(payload):
            return JSONResponse({"error": "Invalid or oversized public Communication Log."}, status_code=400)
        try:
            handle, owner = transcripts.register(payload, request.cookies.get(CLIENT_COOKIE_NAME))
        except OverflowError as error:
            return JSONResponse({"error": str(error)}, status_code=503)
        response = JSONResponse({"handle": handle, "expires_in": TRANSCRIPT_SECONDS}, status_code=201)
        response.set_cookie(CLIENT_COOKIE_NAME, owner, httponly=True, samesite="strict",
                            max_age=TRANSCRIPT_SECONDS, secure=request.url.scheme == "https")
        return response

    @app.get("/api/rider-chat/transcripts/{handle}")
    def read_rider_transcript(handle: str, request: Request):
        record = owned_transcript(handle, request)
        if isinstance(record, Response):
            return record
        if not access.allowed(request.cookies.get(COOKIE_NAME), "rider:" + handle):
            return JSONResponse({"error": "Communication Log locked. Enter the access code again."}, status_code=403)
        record = owned_transcript(handle, request, metadata_only=False)
        if isinstance(record, Response):
            return record
        return JSONResponse({**record, "expires_in": min(access.remaining(request.cookies.get(COOKIE_NAME)), transcripts.remaining(handle))})

    @app.post("/api/rider-chat/transcripts/{handle}/unlock")
    async def unlock_rider_transcript(handle: str, request: Request):
        record = owned_transcript(handle, request)
        if isinstance(record, Response):
            return record
        payload = await bounded_json(request, 1024)
        code = payload.get("code", "") if isinstance(payload, dict) and set(payload) == {"code"} else ""
        token = access.unlock(code if isinstance(code, str) else "", "rider:" + handle, request.cookies.get(COOKIE_NAME))
        if token is None:
            response = JSONResponse({"error": "Incorrect access code. Please try again."}, status_code=403)
            response.delete_cookie(COOKIE_NAME)
            return response
        response = Response(status_code=204)
        set_session(response, request, token)
        return response

    @app.post("/api/rider-chat/transcripts/{handle}/lock")
    def lock_rider_transcript(handle: str, request: Request):
        access.revoke(request.cookies.get(COOKIE_NAME))
        record = owned_transcript(handle, request)
        response = record if isinstance(record, Response) else Response(status_code=204)
        response.delete_cookie(COOKIE_NAME)
        return response

    def case_response(case_id: str, request: Request, error: str = "", status: int = 200):
        try:
            case = store.get_case(case_id)
        except CaseNotFound as missing:
            return HTMLResponse(_page("Not found", f"<p>{escape(str(missing))}</p>"), status_code=404)
        unlocked = not error and access.allowed(request.cookies.get(COOKIE_NAME), case_id)
        chat = log_html(store.log(case_id), case, access.remaining(request.cookies.get(COOKIE_NAME))) if unlocked else locked_html(case_id, error, focus=request.query_params.get("chat_locked") == "1")
        return HTMLResponse(_page(f"Case {case_id}", _ruling_html(case) + _policy_html(case) + chat), status_code=status)

    @app.get("/", response_class=HTMLResponse)
    def home():
        rows = "".join(_dispute_row(d, catalog.trip(d.trip_id)["trip"]) for d in catalog.disputes.values())
        template = (HERE / "console.html").read_text(encoding="utf-8")
        return template.replace("{{SIMULATED}}", escape(SIMULATED)).replace("{{DISPUTES}}", rows).replace("{{COUNT}}", str(len(catalog.disputes))).replace("{{SWITCHES}}", checkboxes_html()).replace("{{MODEL_LABEL}}", escape(model_label)).replace("{{THRESHOLD}}", str(CONFIG.escalation.confidence_threshold))

    @app.post("/api/disputes/{dispute_id}/run", status_code=202)
    def start_run(dispute_id: str, request: Request):
        """Start a run in the background and return its Case ID as soon as the Case exists, so the console can watch it."""
        try:
            dispute = catalog.dispute(dispute_id)
        except UnknownDispute as error:
            return JSONResponse({"error": str(error)}, status_code=404)
        known = {case.case_id for case in store.list_cases()}
        switches = switches_from_query(request.query_params)  # None: the configured defaults

        def work():
            try:
                run_dispute(dispute, store=store, model=model, catalog=catalog, switches=switches)
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
            "calls": [call.model_dump(mode="json") for call in store.calls(case_id)],
            "run_error": run_errors.get(case_id),
        }

    add_review_routes(app, store=store, simulated=SIMULATED, model_label=model_label)
    if model_for is not None:  # the evaluation runs every case on fresh stores, so it needs a way to make a model for each
        add_evaluation_routes(app, catalog=catalog, model_for=model_for, simulated=SIMULATED, model_label=model_label)

    @app.post("/api/classify")
    def classify_description(request: ClassifyRequest):
        """Which category a description belongs to, when none was chosen; a clear error when it fits none."""
        try:
            category = resolve_category(request.category, request.description)
        except IntakeError as error:
            return JSONResponse({"error": str(error)}, status_code=422)
        return {"category": category.value, "chosen": bool(request.category)}

    @app.post("/disputes/{dispute_id}/run")
    def run(dispute_id: str):
        try:
            dispute = catalog.dispute(dispute_id)
        except UnknownDispute as error:
            return HTMLResponse(_page("Not found", f"<p>{escape(str(error))}</p>"), status_code=404)
        case = run_dispute(dispute, store=store, model=model, catalog=catalog)
        return RedirectResponse(f"/cases/{case.case_id}", status_code=303)

    @app.get("/cases/{case_id}", response_class=HTMLResponse)
    def show_case(case_id: str, request: Request):
        return case_response(case_id, request)

    @app.post("/cases/{case_id}/chat/unlock")
    async def unlock_chat(case_id: str, request: Request):
        try:
            store.get_case(case_id)
        except CaseNotFound as error:
            return HTMLResponse(_page("Not found", f"<p>{escape(str(error))}</p>"), status_code=404)
        # Read a plain HTML form without adding a multipart dependency. Never echo the code.
        body = await request.body()
        values = parse_qs(body.decode("utf-8", errors="replace")) if len(body) <= 1024 else {}
        codes = values.get("code", [])
        code = codes[0] if len(codes) == 1 else ""
        token = access.unlock(code, case_id, request.cookies.get(COOKIE_NAME))
        if token is None:
            response = case_response(case_id, request, "Incorrect access code. Please try again.", status=403)
            response.delete_cookie(COOKIE_NAME)
            return response
        response = RedirectResponse(case_path(case_id), status_code=303)
        set_session(response, request, token)
        return response

    @app.post("/cases/{case_id}/chat/lock")
    def lock_chat(case_id: str, request: Request):
        try:
            store.get_case(case_id)
        except CaseNotFound as error:
            return HTMLResponse(_page("Not found", f"<p>{escape(str(error))}</p>"), status_code=404)
        access.revoke(request.cookies.get(COOKIE_NAME))
        response = RedirectResponse(case_path(case_id) + "?chat_locked=1", status_code=303)
        response.delete_cookie(COOKIE_NAME)
        return response

    # API and Prepared Disputes routes take precedence over prototype static paths.
    app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[2] / "prototypes", html=True), name="prototypes")
    return app


def _dispute_row(dispute, trip: dict) -> str:
    """One Dispute in the picker, in the rider app's trip-choice style. The data attributes fill the trip panel."""
    pickup, dropoff = trip["pickup_location"]["name"], trip["dropoff_location"]["name"]
    is_route = dispute.category is DisputeCategory.ROUTE_DEVIATION
    fee = f"{trip['currency']} {trip['paid_net'] if is_route else trip['cancellation_fee']}"
    charge_label = "paid fare" if is_route else "fee"
    when = trip["scheduled_time"][:16].replace("T", " ")
    return (
        f"<button type='button' class='trip-choice' aria-pressed='false' data-dispute='{escape(dispute.dispute_id)}' "
        f"data-category='{escape(dispute.category.value)}' data-pickup='{escape(pickup)}' data-destination='{escape(dropoff)}' "
        f"data-fare='{escape(fee)}' data-when='{escape(when)}' data-filed-by='{escape(dispute.filed_by.value)}' "
        f"data-description='{escape(dispute.description)}'>"
        f"<span class='row'><strong>{escape(dispute.dispute_id)}</strong>"
        f"<span class='tag'>{escape(dispute.category.value.replace('_', ' '))}</span></span>"
        f"<span class='journey'>{escape(pickup)}<small>→ {escape(dropoff)}</small></span>"
        f"<span class='small muted'>{escape(when)} SGT · {escape(fee)} {charge_label}</span></button>"
    )


def _page(title: str, body: str) -> str:
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{escape(title)}</title>"
        f"<link rel='stylesheet' href='/static/console.css'><style>{CHAT_STYLE}</style></head><body class='plain'>"
        f"<p><strong>{SIMULATED}</strong></p><h1>{escape(title)}</h1>{body}"
        "<p><a href='/'>Prepared Disputes</a></p></body></html>"
    )


def _ruling_html(case: Case) -> str:
    ruling = case.ruling
    if ruling is None:
        return f"<h2>Ruling</h2><p>No Ruling. Case status: {escape(case.status.value)}.</p>"
    confidence = "not available"
    if ruling.confidence is not None:
        components = ", ".join(f"{escape(name)} {value}" for name, value in ruling.confidence.components.items())
        confidence = f"{ruling.confidence.value} ({components})"
    if ruling.status is RulingStatus.PROPOSAL:
        reasons = "".join(
            f"<li>{escape(record.trigger.value)}: {escape(record.reason)}</li>"
            for record in ruling.review_triggers
        )
        return (
            "<h2>Proposal — no final decision</h2>"
            f"<p><strong>Case status: {escape(case.status.value)}. "
            "No payment is authorized or executed.</strong></p>"
            f"<h3>Review reasons</h3><ul>{reasons}</ul>"
            f"<p>Confidence: {confidence}</p>"
            f"<p>Proposal reasoning: {escape(ruling.reasoning_summary)}</p>"
        )
    amount = f"{escape(ruling.currency)} {ruling.amount}" if ruling.amount is not None else "none"
    return (
        "<h2>Ruling</h2><ul>"
        f"<li>Outcome: {escape(ruling.outcome.value)} (remedy: {escape(ruling.remedy.value)})</li>"
        f"<li>Amount: {amount}</li>"
        f"<li>Confidence: {confidence}</li>"
        f"<li>Reasoning: {escape(ruling.reasoning_summary)}</li></ul>"
    )


def _policy_html(case: Case) -> str:
    if not case.policy_clauses:
        return ""
    rows = "".join(
        f"<li><strong>{escape(c.clause_id)}</strong> (version {escape(c.version)}): {escape(c.text)}</li>"
        for c in case.policy_clauses
    )
    return f"<h2>Policy</h2><p>{escape(POLICY_SIMULATED)}</p><ul>{rows}</ul>"
