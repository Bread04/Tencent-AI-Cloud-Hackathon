"""Photo metadata, read by code (architecture.md section 5.4). Timestamp alignment is never a model's guess.

A photo's capture time is read from a sidecar file next to it (`seat-stain.png.json`, key `captured_at`), the
mock-data stand-in for EXIF. No sidecar, or one that cannot be read, means the time is unknown.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SLACK = timedelta(minutes=30)  # a photo taken a little before pickup or after the trip still counts as in the window


@dataclass(frozen=True)
class Alignment:
    state: str  # "aligned", "outside_window" or "unknown"
    detail: str


def resolve(photo: str) -> Path:
    path = Path(photo)
    return path if path.is_absolute() else ROOT / path


def capture_time(photo: str) -> datetime | None:
    sidecar = resolve(photo).with_name(resolve(photo).name + ".json")
    try:
        return datetime.fromisoformat(json.loads(sidecar.read_text(encoding="utf-8"))["captured_at"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def timestamp_alignment(captured_at: datetime | None, start: datetime, end: datetime) -> Alignment:
    if captured_at is None:
        return Alignment("unknown", "The photo has no capture time (metadata missing or stripped), so it cannot be placed in the trip window.")
    if start - SLACK <= captured_at <= end + SLACK:
        return Alignment("aligned", f"Captured {captured_at.isoformat()}, inside the trip window {start.isoformat()} to {end.isoformat()} (30 minutes either side allowed).")
    return Alignment("outside_window", f"Captured {captured_at.isoformat()}, outside the trip window {start.isoformat()} to {end.isoformat()}.")
