"""The Judge's stability check (architecture.md section 6.7), a guard against position bias.

The Judge rules a second time with the Submissions read in the other order. Code compares the two passes:
a different outcome, or a Confidence gap above the margin, means the Judge was swayed by order and the
Case is held for a person. The order of the first pass is set by the Case, so it varies between Cases
and never for one Case.
"""

import hashlib
from dataclasses import dataclass

from src.contracts import RulingOutcome


@dataclass(frozen=True)
class StabilityResult:
    agrees: bool
    reason: str  # worded for the Communication Log and the reviewer


def submission_order_flipped(case_id: str) -> bool:
    """True when the first pass reads the Driver's Submission before the Rider's. Fixed per Case, varied across Cases."""
    return int(hashlib.sha256(case_id.encode()).hexdigest(), 16) % 2 == 1


def compare(first: tuple[RulingOutcome, float], second: tuple[RulingOutcome, float], *, margin: float) -> StabilityResult:
    """Each pass is (outcome, Confidence). Rounded, so floating-point noise cannot decide a gap that equals the margin."""
    (outcome_a, confidence_a), (outcome_b, confidence_b) = first, second
    if outcome_a is not outcome_b:
        return StabilityResult(
            False,
            f"The passes disagree on the outcome: {outcome_a.value} ({confidence_a:.2f}), then {outcome_b.value} ({confidence_b:.2f}) "
            "with the Submissions in the other order.",
        )
    gap = round(abs(confidence_a - confidence_b), 2)
    if gap > margin:
        return StabilityResult(
            False,
            f"The passes disagree on Confidence: {confidence_a:.2f}, then {confidence_b:.2f}, a gap of {gap:.2f} above the margin {margin}.",
        )
    return StabilityResult(
        True,
        f"Both passes agree: {outcome_a.value} at {confidence_a:.2f}, then {outcome_b.value} at {confidence_b:.2f} "
        f"with the Submissions in the other order (margin {margin}).",
    )


def unfinished(why: str) -> StabilityResult:
    """The second pass could not be completed, so the first cannot be called stable: the Case is held rather than passed unchecked."""
    return StabilityResult(False, f"The second pass could not be completed ({why}), so the ruling was not checked for order bias.")
