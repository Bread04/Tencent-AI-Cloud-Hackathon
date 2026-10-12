"""Run one prepared Dispute end to end on the model chosen by the environment, and compare with its label.

    MODEL_PROVIDER=openai_compatible MODEL_BASE_URL=... MODEL_API_KEY=... MODEL_NAME=... \
        uv run python -m scripts.try_model DISP-003

With no settings it runs on the scripted stub. The expected label is read here only to print the comparison;
no agent ever sees it. A model that fails ends in review with the reason, never a made-up Ruling.
"""

import json
import sys

from src.api.demo import ReplayModel
from src.intake import DEFAULT_DATA_DIR, load_catalog
from src.llm.factory import environment_with_dotenv, model_from_environment
from src.orchestrator import run_dispute
from src.store import CaseStore


def main(dispute_id: str) -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # model text can hold characters the Windows console codepage cannot print
    catalog, store = load_catalog(), CaseStore()
    model = model_from_environment(environment_with_dotenv(), stub=ReplayModel(store))
    case = run_dispute(catalog.dispute(dispute_id), store=store, model=model, catalog=catalog)
    label = json.loads((DEFAULT_DATA_DIR / f"{dispute_id.lower()}.eval.json").read_text(encoding="utf-8"))

    print(f"{dispute_id}: case {case.case_id} is {case.status.value}")
    for event in store.log(case.case_id):
        print(f"  {event.kind.value}: {event.summary}")
    if case.ruling:
        print(f"ruling: {case.ruling.outcome.value} / {case.ruling.remedy.value} / amount {case.ruling.amount} / "
              f"confidence {case.ruling.confidence.value} / {case.ruling.status.value}")
    else:
        print("ruling: none (held for review)")
    print(f"expected: {label.get('expected_outcome')} / {label.get('expected_remedy')} / amount {label.get('expected_amount')}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "DISP-003")
