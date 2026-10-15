"""Vercel entrypoint: serves the same app as `uvicorn src.api.demo:app`."""

from src.api.demo import app  # noqa: F401
