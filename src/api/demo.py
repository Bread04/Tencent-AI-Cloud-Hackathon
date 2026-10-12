"""The runnable demo: the page wired to the prepared mock Disputes and the scripted stub.

    uv run uvicorn src.api.demo:app

Every run of a Dispute replays that Dispute's own scripted replies (`fixtures/stub/<id>.json`), whatever the
Case ID, so a Dispute can be run any number of times. Replaced by the real model in ticket 08.
"""

from fastapi import FastAPI

from src.api import create_app
from src.intake import load_catalog
from src.llm.adapter import ModelError
from src.llm.stub import StubModel, load_replies
from src.store import CaseStore


class ReplayModel(StubModel):
    """A stub that answers each Case with the script of the Dispute it was filed for."""

    def __init__(self, scripts: dict[str, dict], store: CaseStore):
        super().__init__({})
        self._scripts = scripts
        self._store = store

    def _next_reply(self, case_id: str, agent: str):
        dispute_id = self._store.get_case(case_id).dispute.dispute_id
        script = self._scripts.get(dispute_id, {})
        if agent not in script:
            raise ModelError(f"No scripted reply for {dispute_id}, agent {agent}.")
        return script[agent]


def create_demo_app() -> FastAPI:
    catalog, store = load_catalog(), CaseStore()
    scripts = {dispute_id: load_replies(dispute_id) for dispute_id in catalog.disputes}
    return create_app(store=store, model=ReplayModel(scripts, store), catalog=catalog)


app = create_demo_app()
