"""The one shared repair loop (architecture.md section 8).

A model reply that fails validation, or fails a code rule, is sent back with
the problems written out, up to a fixed number of times. If it is still wrong
the stage fails with the reason, so the Case can go to review. Nothing here
ever invents a reply.
"""

from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from src.llm.adapter import Message, ModelAdapter

T = TypeVar("T", bound=BaseModel)


class StageFailed(Exception):
    """A stage used up its repair budget. The Case goes to review with these problems as the reason."""

    def __init__(self, problems: list[str]):
        super().__init__(" ".join(problems))
        self.problems = problems


FEEDBACK_PREFIX = "Your previous reply was not accepted:\n"


def feedback_message(problems: list[str]) -> Message:
    listed = "\n".join(f"- {problem}" for problem in problems)
    return {"role": "user", "content": f"{FEEDBACK_PREFIX}{listed}\nReply again with a corrected answer."}


def complete_with_repair(
    model: ModelAdapter,
    messages: list[Message],
    *,
    case_id: str,
    agent: str,
    schema: type[T],
    check: Callable[[T], list[str]],
    attempts: int,
    images: list[str] | None = None,
) -> T:
    """Ask for a `schema` reply and return the first one `check` accepts (no problems).

    A reply that does not match the schema counts as a problem too. After
    `attempts` send-backs (so `attempts + 1` calls in all) raises `StageFailed`.
    """
    sent = list(messages)
    problems: list[str] = []
    for _ in range(attempts + 1):
        try:
            reply = model.complete(sent, case_id=case_id, agent=agent, schema=schema, images=images)
        except ValidationError as error:
            problems = [f"The reply did not match the required format: {error}"]
        else:
            problems = check(reply)
            if not problems:
                return reply
        sent = [*sent, feedback_message(problems)]
    raise StageFailed(problems)
