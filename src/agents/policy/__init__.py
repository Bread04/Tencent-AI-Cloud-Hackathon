"""Policy lookup (architecture.md section 5.3, tracer version).

One shared policy source with stable Policy Clause IDs and one version: the
Waypoint set in `prototypes/shared/policies.js`, ported to `data/policy/` by
`scripts/sync_policy.cjs` (a test keeps the two identical). Advocates and the
Judge get the same clauses.

The source is deliberately generic: it sets no wait time and no fee. Those
thresholds are trip data, read from the fare Evidence Item, so a mock case can
carry its own numbers without anyone inventing a rule in policy text.

Not here yet: clause lists for the other categories, role-scoped retrieval,
and precedent (Tier 1).
"""

import json
from pathlib import Path

from src.config import CONFIG
from src.contracts import DisputeCategory, PolicyClause, Remedy, RulingOutcome

POLICY_DIR = Path(__file__).resolve().parents[3] / "data" / "policy"
POLICY_VERSION = "waypoint-singapore-draft-2026-10"
SIMULATED_LABEL = "Draft policy: Waypoint prototype guidance for the demo, not Ryde's approved terms."

# Which source clauses serve each Dispute Category. Both parties' clauses are served to every agent.
CATEGORY_CLAUSES: dict[DisputeCategory, tuple[str, ...]] = {
    DisputeCategory.NO_SHOW_CHARGE: ("R-01", "R-02", "R-03", "R-06", "D-02", "D-03", "D-06", "D-09"),
    DisputeCategory.SAFETY_INCIDENT: ("R-05", "R-06", "D-05", "D-06"),
}

# The Remedy each outcome may carry, per category. The shared policy set does not state this, so it is
# enforced here and by the Judge. An outcome missing from a category's table is not allowed: No-Show has no
# `partially_uphold` because no Policy Clause provides for a partial outcome, so it is all or nothing.
ALLOWED_REMEDIES: dict[DisputeCategory, dict[RulingOutcome, Remedy]] = {
    DisputeCategory.NO_SHOW_CHARGE: {
        RulingOutcome.UPHOLD: Remedy.FEE_REVERSAL,
        RulingOutcome.REJECT: Remedy.NO_ACTION,
    },
    # A Safety Incident Ruling is only ever a proposal for a person (it always escalates); the refund is the Remedy it proposes.
    DisputeCategory.SAFETY_INCIDENT: {
        RulingOutcome.UPHOLD: Remedy.FULL_REFUND,
        RulingOutcome.REJECT: Remedy.NO_ACTION,
    },
}


def policy_for(category: DisputeCategory, directory: Path = POLICY_DIR) -> list[PolicyClause]:
    """The clauses that apply to a Dispute Category; empty if the category has no policy mapped yet."""
    wanted = CATEGORY_CLAUSES.get(category)
    if not wanted:
        return []
    source = json.loads((directory / f"{POLICY_VERSION}.json").read_text(encoding="utf-8"))
    by_id = {clause["clause_id"]: clause for clause in source["clauses"]}
    return [
        PolicyClause(clause_id=clause_id, category=category, text=by_id[clause_id]["text"], version=source["version"])
        for clause_id in wanted
    ]


def material_evidence(category: DisputeCategory) -> dict[str, str]:
    """The category's material-evidence checklist: key -> label shown in the Ruling."""
    return CONFIG.material_evidence[category]
