"""Record each prepared Dispute run on the scripted stub as the JSON the console replays (`?recorded=1`).

    uv run python -m scripts.record_cases

Writes `src/api/static/recorded/<dispute id>.json`, in the same shape as `GET /api/cases/<id>`. The console can
then be built and demonstrated without the orchestrator running. Re-run it when the pipeline's output changes.
"""

import json
from pathlib import Path

from src.intake import load_catalog
from src.llm.stub import StubModel, load_replies
from src.orchestrator import run_dispute
from src.store import CaseStore

OUT = Path(__file__).resolve().parents[1] / "src" / "api" / "static" / "recorded"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = load_catalog()
    for dispute_id, dispute in catalog.disputes.items():
        store = CaseStore()
        model = StubModel({("CASE-0001", agent): reply for agent, reply in load_replies(dispute_id).items()})
        case = run_dispute(dispute, store=store, model=model, catalog=catalog)
        body = {
            "case": case.model_dump(mode="json"),
            "log": [event.model_dump(mode="json") for event in store.log(case.case_id)],
            "run_error": None,
        }
        (OUT / f"{dispute_id}.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
        print(f"recorded {dispute_id}: {len(body['log'])} log events")


if __name__ == "__main__":
    main()
