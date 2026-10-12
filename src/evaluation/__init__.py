"""The evaluation harness (ticket 20): run every mock case and compare the Ruling with its expected-outcome label.

The labels (`data/cases/*.eval.json`) are the harness's alone. The catalog never loads them, no prompt carries
them, and a Case's label is looked up only after that Case has been ruled. A run from the scripted stub proves
the pipeline is wired; a run from a real model is the one worth showing, so every report says which one made it.
"""

import json
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel

from src.agents.escalation import review_package
from src.contracts import Case, CaseStatus, ReviewTrigger, Switches
from src.intake import DEFAULT_DATA_DIR, Catalog
from src.intake.catalog import EVAL_SUFFIX
from src.llm.adapter import ModelAdapter
from src.orchestrator import run_dispute
from src.store import CaseStore


class Label(BaseModel):
    """What a Case should end as. Fields are optional: an ambiguous case has no predetermined outcome."""

    dispute_id: str
    scenario_classification: str | None = None
    expected_outcome: str | None = None
    expected_remedy: str | None = None
    expected_amount: Decimal | None = None
    expected_review_required: bool = False
    acceptable_review_triggers: list[str] = []
    expected_summary: str = ""


class Row(BaseModel):
    dispute_id: str
    scenario: str | None
    expected: str
    actual: str
    confidence: float | None
    judged: bool = True  # False when the model or a stage failed before any Ruling: the case was not judged, which is not a wrong answer
    passed: bool
    why: str  # empty when the row passes


class Report(BaseModel):
    model: str  # which model produced this: the scripted stub, or a named live model
    ran_at: datetime
    rows: list[Row]

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def passed(self) -> int:
        return sum(row.passed for row in self.rows)

    @property
    def unjudged(self) -> int:
        return sum(not row.judged for row in self.rows)

    @property
    def rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def as_json(self) -> dict:
        return {**self.model_dump(mode="json"), "passed": self.passed, "total": self.total, "unjudged": self.unjudged, "rate": self.rate}


def load_labels(directory=DEFAULT_DATA_DIR) -> dict[str, Label]:
    labels = {}
    for path in sorted(directory.glob(f"*{EVAL_SUFFIX}")):
        label = Label.model_validate(json.loads(path.read_text(encoding="utf-8")))
        labels[label.dispute_id] = label
    return labels


def evaluate(
    *,
    catalog: Catalog,
    model_for: Callable[[CaseStore], ModelAdapter],
    switches: Switches,
    model_label: str,
    labels: Mapping[str, Label] | None = None,
) -> Report:
    """Run every prepared Dispute in `catalog` and score it against its label. Labels are read after each Case is ruled."""
    rows, known = [], labels
    for dispute_id, dispute in catalog.disputes.items():
        store = CaseStore()
        case = run_dispute(dispute, store=store, model=model_for(store), catalog=catalog, switches=switches)
        if known is None:  # first look at any label, and only now that a Case has been ruled
            known = load_labels()
        label = known.get(dispute_id)
        rows.append(_score(dispute_id, label, case, review_package(case, store.log(case.case_id)).reasons))
    return Report(model=model_label, ran_at=datetime.now(timezone.utc), rows=rows)


def _score(dispute_id: str, label: Label | None, case: Case, reasons) -> Row:
    triggers = [record.trigger for record in reasons]
    held = case.status is CaseStatus.PENDING_REVIEW
    ruling = case.ruling
    actual = _actual(case, triggers)
    confidence = ruling.confidence.value if ruling and ruling.confidence else None
    if label is None:
        return Row(dispute_id=dispute_id, scenario=None, expected="(none)", actual=actual, confidence=confidence, passed=False, why="There is no expected-outcome label for this case.")
    failure = next((record.reason for record in reasons if record.trigger is ReviewTrigger.STAGE_FAILED), None)
    if failure and ruling is None:
        return Row(
            dispute_id=dispute_id, scenario=label.scenario_classification, expected=_expected(label), actual=actual, confidence=None,
            judged=False, passed=False, why=f"Not judged: a stage failed before any Ruling. {failure[:300]}",
        )
    problems = _problems(label, case, held, triggers)
    return Row(
        dispute_id=dispute_id, scenario=label.scenario_classification, expected=_expected(label), actual=actual,
        confidence=confidence, passed=not problems, why=" ".join(problems),
    )


def _problems(label: Label, case: Case, held: bool, triggers: list[ReviewTrigger]) -> list[str]:
    if case.status is CaseStatus.REJECTED:
        return ["The case was turned away at intake, so it was not ruled (the log has the reason, for example: cannot be resolved yet)."]
    problems = []
    ruling = case.ruling
    if label.expected_review_required:
        if not held:
            problems.append("It should be held for review but it was ruled without one.")
        elif label.acceptable_review_triggers and not {t.value for t in triggers} & set(label.acceptable_review_triggers):
            problems.append(f"It was held, but not for an accepted reason (wanted one of {', '.join(label.acceptable_review_triggers)}).")
    elif held:
        problems.append("It was held for review but it should resolve without a person.")
    if label.expected_outcome is not None:
        if ruling is None:
            problems.append(f"There is no Ruling; the expected outcome was {label.expected_outcome}.")
        else:
            if ruling.outcome.value != label.expected_outcome:
                problems.append(f"The outcome was {ruling.outcome.value} but {label.expected_outcome} was expected.")
            if label.expected_remedy and ruling.remedy.value != label.expected_remedy:
                problems.append(f"The remedy was {ruling.remedy.value} but {label.expected_remedy} was expected.")
            if label.expected_amount is not None and ruling.amount != label.expected_amount:
                problems.append(f"The amount was {ruling.amount} but {label.expected_amount} was expected.")
    return problems


def _expected(label: Label) -> str:
    parts = [label.expected_outcome] if label.expected_outcome else []
    if label.expected_remedy:
        parts.append(label.expected_remedy)
    if label.expected_amount is not None:
        parts.append(f"SGD {label.expected_amount}")
    if label.expected_review_required:
        parts.append("held for review")
    return " · ".join(parts) or "(no outcome set)"


def _actual(case: Case, triggers: list[ReviewTrigger]) -> str:
    if case.status is CaseStatus.REJECTED:
        return "turned away at intake"
    ruling = case.ruling
    parts = [f"{ruling.outcome.value} · {ruling.remedy.value}" + (f" · {ruling.currency} {ruling.amount}" if ruling.amount is not None else "")] if ruling else ["no ruling"]
    if case.status is CaseStatus.PENDING_REVIEW:
        parts.append(f"held for review ({', '.join(t.value for t in triggers) or 'no reason recorded'})")
    return " · ".join(parts)


def render_table(report: Report) -> str:
    """The report as plain text for a terminal, with the model and the pass rate."""
    lines = [f"Evaluation on {report.model}: {report.passed} of {report.total} passed ({report.rate:.0%})"]
    if report.unjudged:
        lines.append(f"{report.unjudged} could not be judged because the model failed, so the pass rate understates the model: run it again.")
    lines.append("")
    width = max([len("case")] + [len(row.dispute_id) for row in report.rows])
    for row in report.rows:
        conf = f"{row.confidence:.2f}" if row.confidence is not None else "-"
        lines.append(f"{'PASS' if row.passed else 'FAIL'}  {row.dispute_id:<{width}}  conf {conf:>4}  expected: {row.expected}  |  actual: {row.actual}")
        if row.why:
            lines.append(f"      why: {row.why}")
    return "\n".join(lines)
