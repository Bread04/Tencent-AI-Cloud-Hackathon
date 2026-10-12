"""The demo's switches in one table.

Each row is one Supporting Agent the console can turn on for a run. The table drives the API (`?name=true`), the
console's checkboxes, the recorded-stream file names (`DISP-003.precedent.stability.json`, names in table order) and
which scripted replies the stub plays. Adding a switch is one row here plus its `Switches` field.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from src.config import CONFIG
from src.contracts import Switches


@dataclass(frozen=True)
class DemoSwitch:
    name: str  # in the query string, the checkbox and the recorded file name
    field: str  # the `Switches` field it turns on
    label: str  # the console checkbox


DEMO_SWITCHES = (
    DemoSwitch("precedent", "policy_precedent", "Use precedent"),
    DemoSwitch("stability", "stability_check", "Stability check"),
    DemoSwitch("routing", "sla_routing", "SLA routing"),
)
TRUE = {"true", "1", "yes", "on"}


def switches_from_query(query: Mapping[str, str]) -> Switches | None:
    """The configured switches with the chosen ones on, or None (the configured defaults) when none is chosen."""
    chosen = {s.field: True for s in DEMO_SWITCHES if str(query.get(s.name, "")).lower() in TRUE}
    return CONFIG.switches.model_copy(update=chosen) if chosen else None


def checkboxes_html() -> str:
    return "\n    ".join(
        f'<label class="switch"><input type="checkbox" data-switch="{s.name}"> {s.label}</label>' for s in DEMO_SWITCHES
    )
