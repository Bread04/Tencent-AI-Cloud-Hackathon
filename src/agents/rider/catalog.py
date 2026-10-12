"""Trusted public Rider records, extracted once from RydeDemo; no private History."""

from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = ROOT / "data/prototype/rider-catalog.json"
POLICY_PATH = ROOT / "data/policy/waypoint-singapore-draft-2026-10.json"


class RiderCatalog:
    def __init__(self, path=CATALOG_PATH):
        self._data = json.loads(Path(path).read_text(encoding="utf-8"))

    def riders(self):
        return deepcopy(self._data["riders"])

    def rider(self, rider_id):
        for rider in self._data["riders"]:
            if rider["id"] == rider_id:
                return deepcopy(rider)
        raise ValueError("Unknown demo rider.")

    def trips(self, rider_id):
        self.rider(rider_id)
        return deepcopy([trip for trip in self._data["trips"] if trip["riderId"] == rider_id])

    def trip(self, rider_id, trip_id):
        self.rider(rider_id)
        for trip in self._data["trips"]:
            if trip["id"] == trip_id and trip["riderId"] == rider_id:
                return deepcopy(trip)
        raise ValueError("This trip is not available to the selected rider.")


def load_policy():
    """The existing synchronized policy JSON includes titles, roles and keywords."""
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
