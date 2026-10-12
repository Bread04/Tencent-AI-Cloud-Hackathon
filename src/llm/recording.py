"""Record every model call so the console can show the real exchanges between the agents and the model.

`RecordingModel` wraps any model adapter. It passes each call straight through and writes down who asked,
what was sent, what came back, how long it took, and whether the call was a retry (and why it was sent back).
Each call also lands in the Communication Log as one `model_call` row. A failure is recorded and then raised
unchanged, so wrapping never changes what an agent sees.
"""

import time
from datetime import datetime, timezone

from pydantic import ValidationError

from src.llm.adapter import Message, ModelAdapter, ModelError
from src.llm.calls import ModelCall
from src.llm.repair import FEEDBACK_PREFIX
from src.store import CaseStore

PROBLEM_LIMIT = 600  # characters of a problem kept per call


class RecordingModel:
    def __init__(self, inner: ModelAdapter, store: CaseStore):
        self._inner = inner
        self._store = store
        self.name = getattr(inner, "name", type(inner).__name__)

    def complete(self, messages: list[Message], *, case_id: str, agent: str, schema=None, images=None):
        calls = self._store.calls(case_id)
        attempt = 1 + sum(1 for call in calls if call.agent == agent)
        sent_back = _why_sent_back(messages)
        started, clock = datetime.now(timezone.utc), time.perf_counter()
        reply, outcome, problem = None, "ok", None
        try:
            result = self._inner.complete(messages, case_id=case_id, agent=agent, schema=schema, images=images)
            reply = result if isinstance(result, str) else result.model_dump_json()
            return result
        except ValidationError as error:
            outcome, problem = "invalid", str(error)
            raise
        except ModelError as error:
            outcome, problem = "failed", str(error)
            raise
        finally:
            self._store.record_call(
                case_id,
                ModelCall(
                    index=len(calls) + 1, agent=agent, attempt=attempt, model=self.name, started_at=started,
                    seconds=round(time.perf_counter() - clock, 3), messages=[dict(m) for m in messages],
                    reply=reply, outcome=outcome, problem=problem[:PROBLEM_LIMIT] if problem else None, sent_back_because=sent_back,
                ),
            )


def _why_sent_back(messages: list[Message]) -> str | None:
    last = messages[-1]["content"] if messages else ""
    if not last.startswith(FEEDBACK_PREFIX):
        return None
    return last.removeprefix(FEEDBACK_PREFIX).removesuffix("\nReply again with a corrected answer.").strip()[:PROBLEM_LIMIT]
