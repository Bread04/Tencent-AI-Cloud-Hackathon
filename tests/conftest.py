"""Every test runs on the scripted stub, whatever is in the developer's `.env` or environment.

A real `MODEL_PROVIDER` there would make the demo-app tests call a live model: slow, flaky and billed.
A real environment variable beats the `.env` file, so setting the stub here is enough.
"""

import pytest


@pytest.fixture(autouse=True)
def tests_use_the_stub_model(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "stub")
