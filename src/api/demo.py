"""The runnable demo: the page wired to the prepared mock Disputes and the scripted stub.

    uv run uvicorn src.api.demo:app

Every run replays the same scripted replies, whatever the Case ID, so a
Dispute can be run any number of times. Replaced by the real model in ticket 08.
"""

from fastapi import FastAPI

from src.api import create_app
from src.intake import load_catalog
from src.llm.stub import StubModel, load_replies
from src.store import CaseStore

DEMO_DISPUTE = "DISP-002"
ANY_CASE = "*"


class ReplayModel(StubModel):
    """A stub that answers every Case with the same script."""

    def _next_reply(self, case_id: str, agent: str):
        return super()._next_reply(ANY_CASE, agent)


def create_demo_app() -> FastAPI:
    script = {(ANY_CASE, agent): reply for agent, reply in load_replies(DEMO_DISPUTE).items()}
    return create_app(store=CaseStore(), model=ReplayModel(script), catalog=load_catalog())


app = create_demo_app()
