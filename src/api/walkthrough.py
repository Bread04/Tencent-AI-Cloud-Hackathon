"""The Demo Day walkthrough as a table (ticket 17), and a rehearsal that runs it.

Each row is one run the presenter makes in the console: which prepared Dispute, which switches they tick first, and
how it must end. `docs/demo-script.md` is the same steps with the words to say; a test keeps the two in step.
`rehearse` runs the rows in order in one store, like the live server, so it also catches one step spoiling a later
one (a learned Override is served to every later No-Show Case).

    uv run python -m scripts.rehearse
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from src.agents.escalation import decide_review
from src.api.demo_switches import DEMO_SWITCHES, switches_from_query
from src.contracts import BalanceOfEvidence, Case, CaseStatus, LogEvent, LogEventKind, PrecedentSource, ReviewDecision, ReviewTrigger, RulingOutcome
from src.intake import Catalog
from src.llm.adapter import ModelAdapter
from src.orchestrator import run_dispute
from src.store import CaseStore

REVIEWER = "Demo reviewer"


@dataclass(frozen=True)
class Step:
    dispute_id: str
    says: str  # what the audience is shown, in a few words
    outcome: RulingOutcome  # the Judge's outcome, final or proposed
    tick: tuple[str, ...] = ()  # switches (by `DemoSwitch.name`) the presenter ticks before this run; they stay ticked
    rules_for: BalanceOfEvidence | None = None  # checked when set
    amount: Decimal | None = None  # always checked: None means the Ruling carries no amount
    confidence: float | None = None  # checked when set: a figure the script quotes
    priority: int | None = None  # checked when set: a figure the script quotes
    held_for: tuple[ReviewTrigger, ...] = ()  # the Case is held for a person for at least these reasons; empty: it is ruled without one
    shows: tuple[LogEventKind, ...] = ()  # Communication Log events this step is there to point at
    evidence_from: tuple[str, ...] = ()  # Evidence Item sources this step is there to point at
    cites: tuple[str, ...] = ()  # Precedents the Ruling cites
    override: str | None = None  # after the run, the reviewer overrides the held Case with this reason
    cites_override: bool = False  # the Ruling cites the Precedent an earlier step's Override added
    skippable: bool = False  # the short version leaves this step out, and its switch unticked


SHOWN, HELD, FOR = LogEventKind, ReviewTrigger, BalanceOfEvidence  # short names so a row reads across
STEPS = (
    # The Core Agents alone: both required categories, and a Ruling each way.
    Step("DISP-003", "No-Show, ruled for the rider who filed it", RulingOutcome.UPHOLD, rules_for=FOR.CLAIMANT, amount=Decimal("5.00"), confidence=0.8),
    Step("DISP-002", "No-Show, ruled for the driver it was filed against", RulingOutcome.REJECT, rules_for=FOR.RESPONDENT, confidence=0.7),
    Step("DISP-008", "Route Deviation, a partial refund computed in code", RulingOutcome.PARTIALLY_UPHOLD, rules_for=FOR.CLAIMANT, amount=Decimal("5.39"), confidence=0.95),
    # Each Supporting Agent in turn, in the order of the console's checkboxes.
    Step("DISP-003", "the Judge is shown past Rulings and cites one", RulingOutcome.UPHOLD, tick=("precedent",), rules_for=FOR.CLAIMANT, amount=Decimal("5.00"),
         shows=(SHOWN.PRECEDENT_RETRIEVED,), cites=("PREC-NS-02",)),
    Step("DISP-003", "the Judge rules twice; the passes disagree, so a person decides", RulingOutcome.UPHOLD, tick=("stability",), amount=Decimal("5.00"),
         held_for=(HELD.STABILITY_DISAGREEMENT,), shows=(SHOWN.STABILITY_CHECK, SHOWN.ESCALATED), skippable=True),
    Step("DISP-005", "a Safety Incident gets top priority and always goes to a person", RulingOutcome.UPHOLD, tick=("routing",),
         held_for=(HELD.SAFETY_INCIDENT,), shows=(SHOWN.PRIORITY_SET, SHOWN.ESCALATED), priority=130),
    Step("DISP-011", "each side's Evidence Agent pulls quoted facts out of the chat", RulingOutcome.UPHOLD, tick=("evidence",), rules_for=FOR.CLAIMANT, amount=Decimal("40.00"),
         evidence_from=("extracted_fact",), skippable=True),
    Step("DISP-011", "the photo is checked and supports the driver who filed", RulingOutcome.UPHOLD, tick=("photos",), rules_for=FOR.CLAIMANT, amount=Decimal("40.00"),
         shows=(SHOWN.PHOTO_ANALYSED,), evidence_from=("photo_finding",)),
    Step("DISP-012", "a photo taken before the trip fails its check, so a person decides", RulingOutcome.REJECT,
         held_for=(HELD.AUTHENTICITY_CHECK,), shows=(SHOWN.PHOTO_ANALYSED, SHOWN.ESCALATED), skippable=True),
    Step("DISP-004", "an unclear Case is held, and the reviewer overrides the proposal", RulingOutcome.REJECT, tick=("learning",), confidence=0.5,
         held_for=(HELD.LOW_CONFIDENCE,), shows=(SHOWN.ESCALATED, SHOWN.REVIEW_DECISION, SHOWN.PRECEDENT_ADDED),
         override="The driver's GPS stops two minutes after arrival, so the full wait is not proven. A no-show fee needs a proven wait."),
    Step("DISP-007", "a later similar Case is shown that Override, and the Judge says why this one differs", RulingOutcome.REJECT, rules_for=FOR.RESPONDENT,
         shows=(SHOWN.PRECEDENT_RETRIEVED,), cites_override=True),
)


@dataclass(frozen=True)
class StepResult:
    step: Step
    switches_on: tuple[str, ...]  # every switch ticked by the end of this step
    switches_sent: tuple[str, ...]  # the ones the console sends for this Dispute
    case: Case  # as the step leaves it: after the Override, when there is one
    log: list[LogEvent]
    problems: list[str]  # empty when the step ended as scripted


def rehearse(*, catalog: Catalog, model_for: Callable[[CaseStore], ModelAdapter], steps: Sequence[Step] = STEPS) -> list[StepResult]:
    """Run the steps in order in one store and say, for each, where it did not end as scripted."""
    store = CaseStore()
    model = model_for(store)
    on: list[str] = []
    results = []
    for step in steps:
        on += step.tick
        dispute = catalog.dispute(step.dispute_id)
        sent = [s.name for s in DEMO_SWITCHES if s.name in on and (dispute.photos or not s.photos_only)]  # the console greys out a photos-only box for a Dispute with no photos
        case = run_dispute(dispute, store=store, model=model, catalog=catalog, switches=switches_from_query({name: "true" for name in sent}))
        problems = _problems(step, case)
        if step.override and case.status is CaseStatus.PENDING_REVIEW and case.ruling is not None:
            case = decide_review(store, case.case_id, reviewer=REVIEWER, decision=ReviewDecision.OVERRIDE, reason=step.override)
        log = store.log(case.case_id)
        missing = [kind.value for kind in step.shows if kind not in {event.kind for event in log}]
        if missing:
            problems.append(f"The log has no {', '.join(missing)} event.")
        results.append(StepResult(step=step, switches_on=tuple(on), switches_sent=tuple(sent), case=case, log=log, problems=problems))
    return results


def _problems(step: Step, case: Case) -> list[str]:
    ruling = case.ruling
    if ruling is None:
        why = "; ".join(record.reason for record in case.review_triggers) or "no reason recorded"
        return [f"There is no Ruling (the Case is {case.status.value}): {why}"]
    problems = []
    if ruling.outcome is not step.outcome:
        problems.append(f"The outcome was {ruling.outcome.value}, not {step.outcome.value}.")
    if ruling.amount != step.amount:
        problems.append(f"The amount was {ruling.amount}, not {step.amount}.")
    if step.confidence is not None and (ruling.confidence is None or ruling.confidence.value != step.confidence):
        problems.append(f"Confidence was {ruling.confidence.value if ruling.confidence else 'missing'}, not {step.confidence}.")
    if step.priority is not None and case.priority != step.priority:
        problems.append(f"The priority was {case.priority}, not {step.priority}.")
    if step.rules_for and ruling.balance_of_evidence is not step.rules_for:
        problems.append(f"It was ruled for the {ruling.balance_of_evidence.value}, not the {step.rules_for.value}.")
    held = case.status is CaseStatus.PENDING_REVIEW
    reasons = {record.trigger for record in ruling.review_triggers}
    if step.held_for and not held:
        problems.append("It should be held for a person but it was ruled without one.")
    elif step.held_for and not set(step.held_for) <= reasons:
        problems.append(f"It was held for {', '.join(sorted(r.value for r in reasons))}, not {', '.join(t.value for t in step.held_for)}.")
    elif held and not step.held_for:
        problems.append(f"It was held for a person ({', '.join(sorted(r.value for r in reasons))}) but it should be ruled without one.")
    sources = {item.source for item in case.evidence}
    if not set(step.evidence_from) <= sources:
        problems.append(f"The evidence has nothing from {', '.join(s for s in step.evidence_from if s not in sources)}.")
    if not set(step.cites) <= set(ruling.cited_precedent_ids):
        problems.append(f"The Ruling cites {ruling.cited_precedent_ids or 'no Precedent'}, not {', '.join(step.cites)}.")
    if step.cites_override:
        learned = [p.precedent_id for p in case.precedents if p.source is PrecedentSource.HUMAN_OVERRIDE]
        if not learned or not set(learned) <= set(ruling.cited_precedent_ids):
            problems.append("The Ruling does not cite a Precedent learned from an Override.")
    return problems


def render(results: Sequence[StepResult]) -> str:
    """The rehearsal as plain text for a terminal: one line per step, then how many passed."""
    labels = {s.name: s.label for s in DEMO_SWITCHES}
    lines = []
    for number, result in enumerate(results, start=1):
        step = result.step
        tick = f"  [tick {', '.join(labels[name] for name in step.tick)}]" if step.tick else ""
        lines.append(f"{'FAIL' if result.problems else 'PASS'}  {number:>2}. {step.dispute_id}{tick}  {step.says}")
        lines += [f"          {problem}" for problem in result.problems]
    passed = sum(not result.problems for result in results)
    return "\n".join([*lines, "", f"{passed} of {len(results)} steps ended as scripted."])
