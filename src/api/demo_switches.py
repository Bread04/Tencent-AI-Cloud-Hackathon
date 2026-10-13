"""The demo's switches in one table.

Each row is one Supporting Agent the console can turn on for a run. The table drives the API (`?name=true`), the
console's URL switches, the recorded-stream file names (`DISP-003.precedent.stability.json`, names in table order) and
which scripted replies the stub plays. Adding a switch is one row here plus its `Switches` field.
"""

from collections.abc import Mapping
import json
from dataclasses import dataclass

from src.config import CONFIG
from src.contracts import Switches


@dataclass(frozen=True)
class DemoSwitch:
    name: str  # in the query string, the checkbox and the recorded file name
    field: str  # the `Switches` field it turns on
    label: str  # the console checkbox
    photos_only: bool = False  # means nothing for a Dispute with no photos, so the console and the recordings leave it out for those
    live_only: bool = False  # changes what a later Case sees, so one recorded stream cannot show it: never in a recording


DEMO_SWITCHES = (
    DemoSwitch("precedent", "policy_precedent", "Use precedent"),
    DemoSwitch("stability", "stability_check", "Stability check"),
    DemoSwitch("routing", "sla_routing", "SLA routing"),
    DemoSwitch("evidence", "evidence_agents", "Evidence agents"),
    DemoSwitch("photos", "image_analysis", "Photo analysis", photos_only=True),
    DemoSwitch("learning", "learning_loop", "Learn from overrides", live_only=True),
)
TRUE = {"true", "1", "yes", "on"}


def switches_from_query(query: Mapping[str, str]) -> Switches | None:
    """The configured switches with the chosen ones on, or None (the configured defaults) when none is chosen."""
    chosen = {s.field: True for s in DEMO_SWITCHES if str(query.get(s.name, "")).lower() in TRUE}
    return CONFIG.switches.model_copy(update=chosen) if chosen else None


def applicable_switches(dispute) -> tuple[DemoSwitch, ...]:
    """The switches a recording of this Dispute can vary: photo analysis only counts when it has photos, and live-only ones never do."""
    return tuple(s for s in DEMO_SWITCHES if not s.live_only and (not s.photos_only or dispute.photos))


def switches_json() -> str:
    """The table as JSON for the console, which reads its URL switches from here instead of repeating the names."""
    return json.dumps([{"name": s.name, "needsPhotos": s.photos_only, "liveOnly": s.live_only} for s in DEMO_SWITCHES])
