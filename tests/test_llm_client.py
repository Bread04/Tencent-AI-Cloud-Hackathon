"""Seam: OpenAICompatibleModel.complete(...). A fake HTTP server stands in for the provider, so no test touches the network."""

import json

import httpx
import pytest
from pydantic import BaseModel, ValidationError

from src.llm import ModelError
from src.llm.client import OpenAICompatibleModel

SECRET = "sk-test-secret-key"


class Verdict(BaseModel):
    outcome: str
    confidence: float


def a_reply(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def a_model(handler, **overrides) -> OpenAICompatibleModel:
    settings = dict(base_url="https://models.example/v1", api_key=SECRET, model="test-model", timeout_seconds=5.0)
    return OpenAICompatibleModel(**{**settings, **overrides}, transport=httpx.MockTransport(handler))


def ask(model, **kwargs):
    return model.complete([{"role": "user", "content": "Rule on this."}], case_id="CASE-0001", agent="judge", **kwargs)


def test_plain_text_is_returned_and_the_request_is_an_openai_chat_completion_with_the_key_in_the_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["auth"], seen["body"] = str(request.url), request.headers["authorization"], json.loads(request.content)
        return httpx.Response(200, json=a_reply("Hello."))

    assert ask(a_model(handler)) == "Hello."

    assert seen["url"] == "https://models.example/v1/chat/completions"
    assert seen["auth"] == f"Bearer {SECRET}"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["messages"] == [{"role": "user", "content": "Rule on this."}]
    assert "response_format" not in seen["body"]


def test_a_schema_is_requested_as_json_schema_and_the_reply_is_returned_validated():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=a_reply('{"outcome": "reject", "confidence": 0.8}'))

    verdict = ask(a_model(handler), schema=Verdict)

    assert verdict == Verdict(outcome="reject", confidence=0.8)
    asked_for = seen["body"]["response_format"]
    assert asked_for["type"] == "json_schema"
    assert asked_for["json_schema"]["name"] == "Verdict"
    assert asked_for["json_schema"]["schema"]["properties"].keys() == {"outcome", "confidence"}


@pytest.mark.parametrize("content", ['{"outcome": "reject"}', "not json at all", "{}"])
def test_a_reply_that_breaks_the_schema_raises_validation_error_so_the_repair_loop_can_feed_it_back(content):
    model = a_model(lambda request: httpx.Response(200, json=a_reply(content)))

    with pytest.raises(ValidationError):
        ask(model, schema=Verdict)


def test_a_reply_wrapped_in_a_json_code_fence_is_still_read():
    fenced = '```json\n{"outcome": "reject", "confidence": 0.8}\n```'
    model = a_model(lambda request: httpx.Response(200, json=a_reply(fenced)))

    assert ask(model, schema=Verdict).outcome == "reject"


def test_a_timeout_is_a_model_error_not_a_hang():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ModelError, match="timed out after 5"):
        ask(a_model(handler))


def test_an_unreachable_provider_is_a_model_error_with_a_clear_message():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(ModelError, match="could not be reached"):
        ask(a_model(handler))


@pytest.mark.parametrize("status", [401, 429, 500, 503])
def test_an_http_error_is_a_model_error_naming_the_status_and_never_the_key(status):
    model = a_model(lambda request: httpx.Response(status, text=f"denied for {SECRET}"))

    with pytest.raises(ModelError) as error:
        ask(model)

    assert str(status) in str(error.value)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize("body", [{}, {"choices": []}, {"choices": [{"message": {"content": None}}]}])
def test_a_reply_with_no_content_is_a_model_error(body):
    model = a_model(lambda request: httpx.Response(200, json=body))

    with pytest.raises(ModelError, match="no content"):
        ask(model)


def test_images_are_sent_as_image_parts_on_the_last_message():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=a_reply("A dent."))

    ask(a_model(handler), images=["https://photos.example/car.jpg"])

    parts = seen["body"]["messages"][-1]["content"]
    assert parts[0] == {"type": "text", "text": "Rule on this."}
    assert parts[1] == {"type": "image_url", "image_url": {"url": "https://photos.example/car.jpg"}}


def test_the_key_is_not_part_of_the_models_repr_so_it_cannot_leak_into_a_log():
    model = a_model(lambda request: httpx.Response(200, json=a_reply("x")))

    assert SECRET not in repr(model)
