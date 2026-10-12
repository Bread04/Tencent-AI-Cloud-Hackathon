"""The arguments a Judge must assess, numbered by code so the model refers to them by reference.

An argument is an advocate's claim or one of its counter-arguments. Matching free
text would let a model quietly skip one, so each gets a reference such as
`rider_advocate#counter-1` and the draft is checked against the full list.
"""

from dataclasses import dataclass

from src.contracts import Advocate, Submission


@dataclass(frozen=True)
class Argument:
    ref: str
    author: Advocate
    text: str


def arguments_in(*submissions: Submission) -> list[Argument]:
    found = []
    for submission in submissions:
        author = submission.author
        found.append(Argument(f"{author.value}#claim", author, submission.claim_restated))
        for number, counter in enumerate(submission.counter_arguments, start=1):
            found.append(Argument(f"{author.value}#counter-{number}", author, counter.argument))
    return found


def assessment_problems(arguments: list[Argument], refs: list[str]) -> list[str]:
    """Sentences, written to be fed back to the model, for every way the draft misses the list."""
    required = {argument.ref for argument in arguments}
    problems = []
    for ref in dict.fromkeys(refs):
        if ref not in required:
            problems.append(f"{ref} is not an argument in either Submission, so it cannot be assessed.")
        elif refs.count(ref) > 1:
            problems.append(f"{ref} is assessed more than once; assess each argument exactly once.")
    for argument in arguments:
        if argument.ref not in refs:
            problems.append(f"{argument.ref} has no assessment; every argument in both Submissions must be assessed.")
    return problems
