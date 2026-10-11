"""Policy lookup (architecture.md section 5.3, tracer version).

One shared mock policy with stable Policy Clause IDs and one version, read from
`data/policy/`. Advocates and the Judge get the same clauses. Not here yet
(Tier 1): precedent and the Policy & Precedent Agent's roles and switch.
"""

import json
from pathlib import Path

from src.config import CONFIG
from src.contracts import DisputeCategory, PolicyClause

POLICY_DIR = Path(__file__).resolve().parents[3] / "data" / "policy"
SIMULATED_LABEL = "Simulated policy: mock rules for the demo, not Ryde's real policy."


def policy_for(category: DisputeCategory, directory: Path = POLICY_DIR) -> list[PolicyClause]:
    """The clauses that apply to a Dispute Category; empty if the category has no policy yet."""
    path = directory / f"{category.value}.json"
    if not path.exists():
        return []
    document = json.loads(path.read_text(encoding="utf-8"))
    return [PolicyClause.model_validate(clause) for clause in document["clauses"]]


def material_evidence(category: DisputeCategory) -> dict[str, str]:
    """The category's material-evidence checklist: key -> label shown in the Ruling."""
    return CONFIG.material_evidence[category]
