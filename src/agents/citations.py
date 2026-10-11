"""Refuses a Submission or Ruling that cites something outside the sealed evidence and the policy given.

Ticket 03 raises on the first failure. Repair attempts with the error fed back
arrive with the real advocates (04) and the real Judge (05).
"""

from src.contracts import Case, Ruling, Submission, citation_errors


class CitationError(Exception):
    """A citation to an Evidence Item or Policy Clause that does not exist, or a missing item cited as fact."""


def require_valid_citations(document: Submission | Ruling, case: Case) -> None:
    errors = citation_errors(document, case.evidence, case.policy_clauses, case.precedents)
    if errors:
        raise CitationError(" ".join(errors))
