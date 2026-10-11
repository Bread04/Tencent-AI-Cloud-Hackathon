"""The model adapter (architecture.md section 6.4).

One function, `complete`: messages and optional images in, text or a
schema-validated object out. Agents depend on this interface only, so the
offline stub and the real client (ticket 08) are interchangeable.
"""

from typing import Protocol, TypeVar, overload

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

Message = dict[str, str]  # {"role": "system" | "user" | "assistant", "content": "..."}


class ModelError(Exception):
    """The model could not give a reply (unreachable, timed out, nothing scripted).

    Callers fail the stage to review; they never make up a reply.
    """


class ModelAdapter(Protocol):
    @overload
    def complete(
        self, messages: list[Message], *, case_id: str, agent: str, schema: None = None, images: list[str] | None = None
    ) -> str: ...

    @overload
    def complete(
        self, messages: list[Message], *, case_id: str, agent: str, schema: type[T], images: list[str] | None = None
    ) -> T: ...

    def complete(self, messages, *, case_id, agent, schema=None, images=None):
        """Return the model's reply.

        `case_id` and `agent` say who is asking (the stub keys its script on them).
        With `schema`, the reply is requested as schema-constrained JSON and
        returned as a validated instance; a reply that breaks the schema raises
        pydantic's `ValidationError`, whose text can be fed back for a repair attempt.
        Without `schema`, the reply is plain text.
        `images` is the vision entry point: paths or URLs of photos.
        """
        ...
