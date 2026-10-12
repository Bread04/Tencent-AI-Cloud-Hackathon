"""Choose the model from the environment: one setting, `MODEL_PROVIDER`, switches the stub and the real model.

    MODEL_PROVIDER=stub                  (the default)  scripted replies, no network
    MODEL_PROVIDER=openai_compatible     a real model; needs MODEL_BASE_URL, MODEL_API_KEY and MODEL_NAME

Credentials are read only from the environment (see `.env.example`) and are never in the repo.
"""

from collections.abc import Mapping

from src.config import CONFIG
from src.llm.adapter import ModelAdapter
from src.llm.client import OpenAICompatibleModel

REAL = "openai_compatible"
STUB = "stub"
REQUIRED = ("MODEL_BASE_URL", "MODEL_API_KEY", "MODEL_NAME")


class ModelNotConfigured(Exception):
    """The environment asks for something that cannot be built, with the setting to fix."""


def model_from_environment(env: Mapping[str, str], *, stub: ModelAdapter) -> ModelAdapter:
    provider = env.get("MODEL_PROVIDER", STUB)
    if provider == STUB:
        return stub
    if provider != REAL:
        raise ModelNotConfigured(f"MODEL_PROVIDER must be '{STUB}' or '{REAL}', not '{provider}'.")
    missing = [name for name in REQUIRED if not env.get(name)]
    if missing:
        raise ModelNotConfigured(f"MODEL_PROVIDER is '{REAL}' but {', '.join(missing)} is not set.")
    return OpenAICompatibleModel(
        base_url=env["MODEL_BASE_URL"],
        api_key=env["MODEL_API_KEY"],
        model=env["MODEL_NAME"],
        timeout_seconds=_timeout(env),
    )


def _timeout(env: Mapping[str, str]) -> float:
    raw = env.get("MODEL_TIMEOUT_SECONDS")
    if raw is None:
        return CONFIG.model.timeout_seconds
    try:
        seconds = float(raw)
    except ValueError:
        seconds = 0.0
    if seconds <= 0:
        raise ModelNotConfigured(f"MODEL_TIMEOUT_SECONDS must be a positive number of seconds, not '{raw}'.")
    return seconds
