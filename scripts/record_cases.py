"""Record each prepared Dispute run on the scripted stub as the JSON the console replays (`?recorded=1`).

    uv run python -m scripts.record_cases

Writes `src/api/static/recorded/<dispute id>.json`, in the same shape as `GET /api/cases/<id>`. The console can
then be built and demonstrated without the orchestrator running. Re-run it when the pipeline's output changes.
"""

import itertools
import json
from pathlib import Path

from src.intake import load_catalog
from src.api.demo_switches import DEMO_SWITCHES, applicable_switches
from src.config import CONFIG
from src.llm.stub import StubModel, load_replies
from src.orchestrator import run_dispute
from src.store import CaseStore

OUT = Path(__file__).resolve().parents[1] / "src" / "api" / "static" / "recorded"


def main(dispute_ids: list[str] | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = load_catalog()
    for dispute_id, dispute in catalog.disputes.items():
        if dispute_ids and dispute_id not in dispute_ids:
            continue
        applicable = applicable_switches(dispute)
        for flags in itertools.product([False, True], repeat=len(applicable)):  # every combination of the switches that can change this Dispute
            variants = tuple(s.name for s, on in zip(applicable, flags) if on)
            store = CaseStore()
            model = StubModel({("CASE-0001", agent): reply for agent, reply in load_replies(dispute_id, *variants).items()})
            on = {s.field: s.name in variants for s in DEMO_SWITCHES}
            case = run_dispute(dispute, store=store, model=model, catalog=catalog, switches=CONFIG.switches.model_copy(update=on) if variants else None)
            body = {
                "case": case.model_dump(mode="json"),
                "log": [event.model_dump(mode="json") for event in store.log(case.case_id)],
                "calls": [call.model_dump(mode="json") for call in store.calls(case.case_id)],
                "run_error": None,
            }
            name = ".".join([dispute_id, *variants]) + ".json"
            (OUT / name).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
            print(f"recorded {name}: {len(body['log'])} log events")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispute", action="append", help="Record only this prepared dispute (repeatable).")
    main(parser.parse_args().dispute)
