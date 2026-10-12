"""The runnable demo: the page wired to the prepared mock Disputes and the scripted stub.

    uv run uvicorn src.api.demo:app

By default every Case replays its stored Dispute's prepared script independently.
Set MODEL_PROVIDER=openai_compatible (and the credentials in `.env.example`) to run on a real model instead.
"""

from copy import deepcopy

from fastapi import FastAPI

from src.api import create_app
from src.intake import load_catalog
from src.llm.stub import StubModel, load_replies
from src.llm.adapter import ModelError
from src.llm.factory import environment_with_dotenv, model_from_environment
from src.store import CaseStore

PREPARED_DISPUTES = ("DISP-002", "DISP-003", "DISP-004")


class ReplayModel(StubModel):
    """Resolve scripts through the Case store, with a fresh reply sequence per Case."""

    def __init__(self, store: CaseStore, scripts: dict | None = None):
        super().__init__({})
        self._store = store
        self._prepared = deepcopy(scripts) if scripts is not None else {
            dispute_id: load_replies(dispute_id) for dispute_id in PREPARED_DISPUTES
        }
        # With the precedent switch on, the Judge cites the precedents it was shown (the same script otherwise).
        self._prepared_with_precedent = deepcopy(scripts) if scripts is not None else {
            dispute_id: load_replies(dispute_id, "precedent") for dispute_id in PREPARED_DISPUTES
        }

    def _next_reply(self, case_id: str, agent: str):
        case = self._store.get_case(case_id)
        dispute_id = case.dispute.dispute_id
        prepared = self._prepared_with_precedent if case.switches.policy_precedent else self._prepared
        if dispute_id not in prepared:
            raise ModelError(f"ReplayModel has no prepared script for dispute {dispute_id} (case {case_id}).")
        key = (case_id, agent)
        if key not in self._script:
            if agent not in prepared[dispute_id]:
                raise ModelError(f"ReplayModel has no scripted reply for dispute {dispute_id}, agent {agent}.")
            self._script[key] = deepcopy(prepared[dispute_id][agent])
        return super()._next_reply(case_id, agent)


def create_demo_app() -> FastAPI:
    store = CaseStore()
    env = environment_with_dotenv()
    model = model_from_environment(env, stub=ReplayModel(store))
    label = f"Live model: {env['MODEL_NAME']}" if env.get("MODEL_PROVIDER") == "openai_compatible" else "Scripted replies"
    return create_app(store=store, model=model, catalog=load_catalog(), model_label=label)


app = create_demo_app()
