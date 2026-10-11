"""The bare page: pick a prepared Dispute, run it, see the Ruling and the Communication Log.

Plain server-rendered HTML. The real demo UI is ticket 07.
Everything shown is Mock Data and says so.
"""

from html import escape

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from src.agents.policy import SIMULATED_LABEL as POLICY_SIMULATED
from src.contracts import Case, LogEvent
from src.intake import Catalog, UnknownDispute
from src.llm.adapter import ModelAdapter
from src.orchestrator import run_dispute
from src.store import CaseNotFound, CaseStore

SIMULATED = "Simulated: all trips, evidence, policy and payments on this page are mock data."


def create_app(*, store: CaseStore, model: ModelAdapter, catalog: Catalog) -> FastAPI:
    app = FastAPI(title="Ryde Dispute Resolution (simulated)")

    @app.get("/", response_class=HTMLResponse)
    def home():
        rows = "".join(
            f"<li>{escape(d.dispute_id)} ({escape(d.category.value)}): {escape(d.description)} "
            f"<form method='post' action='/disputes/{escape(d.dispute_id)}/run' style='display:inline'>"
            "<button>Run</button></form></li>"
            for d in catalog.disputes.values()
        )
        return _page("Prepared Disputes", f"<ul>{rows}</ul>")

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


def _page(title: str, body: str) -> str:
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>{escape(title)}</title></head><body>"
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
