"""The runnable demo: the page wired to the prepared mock Disputes and the scripted stub.

    uv run uvicorn src.api.demo:app

By default every Case replays its stored Dispute's prepared script independently.
Set MODEL_PROVIDER=openai_compatible (and the credentials in `.env.example`) to run on a real model instead.
"""

from copy import deepcopy

from fastapi import FastAPI

from src.api import create_app
from src.api.demo_switches import DEMO_SWITCHES
from src.intake import load_catalog
from src.llm.stub import StubModel, load_replies
from src.llm.adapter import ModelError
from src.llm.factory import environment_with_dotenv, model_from_environment
from src.store import CaseStore

PREPARED_DISPUTES = ("DISP-002", "DISP-003", "DISP-004", "DISP-005", "DISP-006")


class ReplayModel(StubModel):
    """Resolve scripts through the Case store, with a fresh reply sequence per Case.

    The script follows the Case's switches: with the precedent switch on the Judge cites the precedents it was
    shown, and with the stability check on the second pass has its own reply (the same as the first by default).
    """

    def __init__(self, store: CaseStore, scripts: dict | None = None):
        super().__init__({})
        self._store = store
        self._custom = deepcopy(scripts) if scripts is not None else None  # tests hand in their own scripts
        self._loaded: dict[tuple, dict] = {}

    def _replies_for(self, case) -> dict | None:
        dispute_id = case.dispute.dispute_id
        if self._custom is not None:
            return self._custom.get(dispute_id)
        if dispute_id not in PREPARED_DISPUTES:
            return None
        variants = tuple(s.name for s in DEMO_SWITCHES if getattr(case.switches, s.field))  # a missing variant file keeps the base replies
        if (dispute_id, variants) not in self._loaded:
            self._loaded[(dispute_id, variants)] = load_replies(dispute_id, *variants)
        return self._loaded[(dispute_id, variants)]

    def _next_reply(self, case_id: str, agent: str):
        case = self._store.get_case(case_id)
        dispute_id = case.dispute.dispute_id
        replies = self._replies_for(case)
        if replies is None:
            raise ModelError(f"ReplayModel has no prepared script for dispute {dispute_id} (case {case_id}).")
        key = (case_id, agent)
        if key not in self._script:
            scripted = replies.get(agent, replies.get("judge") if agent == "judge_second_pass" else None)
            if scripted is None:
                raise ModelError(f"ReplayModel has no scripted reply for dispute {dispute_id}, agent {agent}.")
            self._script[key] = deepcopy(scripted)
        return super()._next_reply(case_id, agent)


def create_demo_app() -> FastAPI:
    store = CaseStore()
    env = environment_with_dotenv()
    model = model_from_environment(env, stub=ReplayModel(store))
    label = f"Live model: {env['MODEL_NAME']}" if env.get("MODEL_PROVIDER") == "openai_compatible" else "Scripted replies"
    return create_app(store=store, model=model, catalog=load_catalog(), model_label=label)


app = create_demo_app()
