"""The real model: a client for any OpenAI-compatible chat endpoint (architecture.md sections 6.4 and 8).

Every call has a timeout. A timeout, an unreachable provider or an HTTP error is a
`ModelError` with a clear message, never a hang and never an invented reply. A reply that
breaks the schema raises pydantic's `ValidationError`, so the shared repair loop can feed
the problem back. The API key lives only in the Authorization header: it is not in the
repr and is never put in an error message.
"""

import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import TypeVar

import httpx
from pydantic import BaseModel

from src.llm.adapter import Message, ModelError

T = TypeVar("T", bound=BaseModel)

FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


class OpenAICompatibleModel:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        structured_output: str = "json_schema",
        transport: httpx.BaseTransport | None = None,
    ):
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._where = _without_secrets(self._url)  # what messages and the repr may show
        self._api_key = api_key
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._model = model
        self._timeout = timeout_seconds
        self._structured_output = structured_output  # json_schema, or json_object for providers without schema support
        self._transport = transport

    def __repr__(self) -> str:
        return f"OpenAICompatibleModel(url={self._where!r}, model={self._model!r})"

    def complete(self, messages: list[Message], *, case_id: str, agent: str, schema: type[T] | None = None, images: list[str] | None = None):
        if schema is not None and self._structured_output == "json_object":
            messages = _with_schema_in_prompt(messages, schema)
        body: dict = {"model": self._model, "messages": _with_images(messages, images, agent)}
        if schema is not None:
            body["response_format"] = (
                {"type": "json_object"}
                if self._structured_output == "json_object"
                else {"type": "json_schema", "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()}}
            )
        content = self._post(body, agent)
        if schema is None:
            return content
        return schema.model_validate_json(_unfenced(content))

    def _post(self, body: dict, agent: str) -> str:
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as http:
                response = http.post(self._url, json=body, headers=self._headers)
        except httpx.TimeoutException as error:
            raise ModelError(f"The model timed out after {self._timeout:g} seconds (agent {agent}).") from error
        except httpx.HTTPError as error:
            raise ModelError(f"The model could not be reached at {self._where} ({type(error).__name__}).") from error
        if response.status_code >= 400:
            raise ModelError(f"The model returned HTTP {response.status_code} (agent {agent}).{self._provider_message(response)}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            content = None
        if not content:
            raise ModelError(f"The model returned no content (agent {agent}).")
        return content

    def _provider_message(self, response: httpx.Response) -> str:
        """The provider's own explanation, when it sends one, with the key scrubbed.

        Gateways such as OpenRouter wrap the real reason: {"error": {"message": "Provider returned error",
        "metadata": {"raw": "<the upstream error>"}}}, so the upstream text is preferred.
        """
        try:
            error = response.json()["error"]
            message = error["message"]
        except (ValueError, KeyError, TypeError):
            return ""
        raw = (error.get("metadata") or {}).get("raw") if isinstance(error, dict) else None
        if isinstance(raw, str) and raw:
            try:
                raw = json.loads(raw).get("message", raw)
            except (ValueError, AttributeError):
                pass
            message = raw
        if not isinstance(message, str):
            return ""
        return " " + message.replace(self._api_key, "[key]")[:240]


def _unfenced(content: str) -> str:
    """Some providers wrap JSON in a code fence even when asked for plain JSON."""
    match = FENCE.match(content.strip())
    return match.group(1) if match else content


def _with_schema_in_prompt(messages: list[Message], schema: type[BaseModel]) -> list[Message]:
    """For providers that accept only plain JSON mode: state the schema in the last message instead."""
    *rest, last = messages
    ask = "\n\nReply with one JSON object that matches this JSON Schema, and nothing else:\n" + json.dumps(schema.model_json_schema())
    return [*rest, {**last, "content": last["content"] + ask}]


def _without_secrets(url: str) -> str:
    """The URL with any user:password and query string removed, so a key placed there cannot leak into a message."""
    parsed = httpx.URL(url)
    return f"{parsed.scheme}://{parsed.host}{':' + str(parsed.port) if parsed.port else ''}{parsed.path}"


def _with_images(messages: list[Message], images: list[str] | None, agent: str) -> list[dict]:
    if not images:
        return [dict(message) for message in messages]
    *rest, last = messages
    parts = [{"type": "text", "text": last["content"]}] + [{"type": "image_url", "image_url": {"url": _image_url(image, agent)}} for image in images]
    return [*(dict(message) for message in rest), {**last, "content": parts}]


def _image_url(image: str, agent: str) -> str:
    """A URL passes through; a local file is sent inline as a data URL."""
    if image.startswith(("http://", "https://", "data:")):
        return image
    path = Path(image)
    try:
        data = path.read_bytes()
    except OSError as error:
        raise ModelError(f"The image {path.name} could not be read (agent {agent}).") from error
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"
