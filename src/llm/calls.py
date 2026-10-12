"""The record of one model call. Not part of the shared contract: it explains a run, it is not a result."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ModelCall(BaseModel):
    """One request to the model and what came of it."""

    index: int
    agent: str
    attempt: int  # 1 for the first call by this agent on this Case, 2 for the first retry, and so on
    model: str
    started_at: datetime
    seconds: float
    messages: list[dict]
    reply: str | None = None
    outcome: Literal["ok", "invalid", "failed"]  # replied, replied with the wrong shape, or no reply at all
    problem: str | None = None
    sent_back_because: str | None = None  # set on a retry: why the previous reply was refused
