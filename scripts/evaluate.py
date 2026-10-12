"""Run every prepared mock case and print how each compares with its expected outcome.

    uv run python -m scripts.evaluate

It runs on the model chosen by `.env` or the environment (the scripted stub by default; see `.env.example`), and
the report says which one produced it. The exit code is 0 when every case passes and 1 otherwise, so it can gate a push.
"""

import sys

from src.api.demo import ReplayModel
from src.config import CONFIG
from src.evaluation import evaluate, render_table
from src.intake import load_catalog
from src.llm.factory import environment_with_dotenv, model_from_environment


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # model text can hold characters the Windows console codepage cannot print
    env = environment_with_dotenv()
    live = env.get("MODEL_PROVIDER") == "openai_compatible"
    label = f"Live model: {env['MODEL_NAME']}" if live else "Scripted replies"
    report = evaluate(
        catalog=load_catalog(),
        model_for=lambda store: model_from_environment(env, stub=ReplayModel(store)),
        switches=CONFIG.switches.model_copy(update={"sla_routing": True, "image_analysis": True}),  # Safety Incidents are only resolvable with routing on
        model_label=label,
    )
    print(render_table(report))
    return 0 if report.passed == report.total else 1


if __name__ == "__main__":
    sys.exit(main())
