"""Offline stub of the model adapter: scripted replies per Case, no network."""

import json

from src.llm.adapter import ModelError

Reply = str | dict
Script = dict[tuple[str, str], Reply | list[Reply]]


class StubModel:
    """Returns the replies it was scripted with, keyed by (case_id, agent).

        StubModel({
            ("CASE-0001", "rider_advocate"): {...a Submission as a dict...},
            ("CASE-0001", "judge"): [first_reply, second_reply],   # one per call, in order
        })

    A single reply is returned on every call; a list is used up one call at a
    time. A call with nothing scripted raises `ModelError`.
    Every call is recorded in `calls` so tests can inspect what was sent.
    """

    def __init__(self, script: Script):
        self._script = {key: list(reply) if isinstance(reply, list) else reply for key, reply in script.items()}
        self.calls: list[dict] = []

    def complete(self, messages, *, case_id, agent, schema=None, images=None):
        self.calls.append({"case_id": case_id, "agent": agent, "messages": messages, "images": images, "schema": schema})

        reply = self._next_reply(case_id, agent)
        if schema is None:
            return reply if isinstance(reply, str) else json.dumps(reply)
        if isinstance(reply, str):
            return schema.model_validate_json(reply)
        return schema.model_validate(reply)

    def _next_reply(self, case_id: str, agent: str) -> Reply:
        key = (case_id, agent)
        if key not in self._script:
            raise ModelError(f"StubModel has no scripted reply for case {case_id}, agent {agent}.")
        scripted = self._script[key]
        if not isinstance(scripted, list):
            return scripted
        if not scripted:
            raise ModelError(f"StubModel has used up its scripted replies for case {case_id}, agent {agent}.")
        return scripted.pop(0)
