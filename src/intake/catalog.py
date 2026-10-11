"""Loads the prepared mock cases from `data/cases/`. Mock Data, always simulated."""

import json
from dataclasses import dataclass
from pathlib import Path

from src.contracts import Dispute

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "cases"
EVAL_SUFFIX = ".eval.json"


class UnknownDispute(KeyError):
    pass


class UnknownTrip(KeyError):
    pass


@dataclass(frozen=True)
class Catalog:
    disputes: dict[str, Dispute]
    trips: dict[str, dict]  # trip_id -> the Trip record: trip, gps_telemetry, chat_logs, histories, ...

    def dispute(self, dispute_id: str) -> Dispute:
        if dispute_id not in self.disputes:
            raise UnknownDispute(f"No prepared Dispute with ID {dispute_id}.")
        return self.disputes[dispute_id]

    def trip(self, trip_id: str) -> dict:
        if trip_id not in self.trips:
            raise UnknownTrip(f"No Trip with ID {trip_id}.")
        return self.trips[trip_id]


def load_catalog(directory: Path = DEFAULT_DATA_DIR) -> Catalog:
    disputes: dict[str, Dispute] = {}
    trips: dict[str, dict] = {}
    for path in sorted(directory.glob("*.json")):
        if path.name.endswith(EVAL_SUFFIX):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        dispute = Dispute.model_validate(record["dispute"])
        disputes[dispute.dispute_id] = dispute
        trips[record["trip"]["trip_id"]] = record
    return Catalog(disputes=disputes, trips=trips)
