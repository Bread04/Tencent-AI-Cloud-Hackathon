---
title: Correct prepared No-Show demo replies and pending review
type: bugfix
created: 2026-10-12
status: done
baseline_commit: 57e2aa5e4fb19ce853f16a8bd7d19720d2241b7c
review_loop_iteration: 0
context:
  - AGENTS.md
  - GLOSSARY.md
  - docs/adr/0001-history-withheld-from-judge.md
  - docs/adr/0002-thresholds-come-from-trip-data-not-policy-text.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

The prepared backend demo currently answers every dispute with DISP-002's script. Fix this first demo problem using case-specific scripted Rider Advocate, Driver Advocate and Judge responses. DISP-002 keeps its existing result; DISP-003 reverses the SGD 5 fee; DISP-004 produces a proposal pending review, with no final decision or payment authorization. The user explicitly approved these responses and the small review-status change.

## Boundaries & Constraints

Always preserve source-grounded claims, shared policy clauses, code-computed amounts and confidence, citations, sealed evidence and the communication log. Resolve the dispute through the Case store, independent of Case ID numbering. Mark everything as simulated. Preserve preexisting local edits.

Ask first before new policy rules, expanded features or remote Git operations. Never read evaluation labels in runtime code, fabricate evidence, use History to decide fault, change workflow.md, redesign the app, or build Route Deviation or a full human-review service in this fix. The styled report prototype is outside scope; this fixes the prepared backend demo.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected behavior | Error |
| --- | --- | --- | --- |
| Driver wins | DISP-002 | Final reject/no_action, existing response preserved | None |
| Rider wins | DISP-003 | Final uphold/fee_reversal, SGD 5.00 computed from fare evidence | None |
| Ambiguous | DISP-004 | Balanced evidence proposal, Case pending_review; visible no final decision | None |
| Repeated/mixed order | Run 004, 003, 002, 004 | Correct independent responses and stored pages each time | None |
| Unknown script | Valid stored dispute without a fixture | No fallback to another dispute's response | Clear ModelError |
| Low confidence | Valid Judge draft below configured threshold | Proposal with low_confidence trigger | None |
| Evaluation isolation | Catalog/model runtime reads | No *.eval.json read | None |

</frozen-after-approval>

## Code Map

- `src/api/demo.py`: ReplayModel currently maps every Case to wildcard DISP-002 replies. Bind it to the same CaseStore passed to create_app; route using the stored dispute_id. Load prepared fixtures only; unknown script errors must be explicit. Keep repeated runs independent, including any list replies.
- `fixtures/stub/DISP-002.json`: preserve unchanged. Add DISP-003.json and DISP-004.json in the same schema. Read original `data/cases/disp-003.json` and `disp-004.json` to ground every claim and cite EV-GPS-1, EV-CHAT-1, EV-FARE-1, EV-RIDERLOC-1 as appropriate. Use existing shared R-02/R-03/D-02/D-03 clauses.
- `src/agents/judge/__init__.py`: compute confidence as before; attach balanced_evidence and low_confidence triggers when applicable and make triggered rulings proposals. Do not invent confidence scores. DISP-004 has arguable policy fit and balanced evidence because location coverage ends after two minutes; elapsed eight minutes is not continuous presence. Its required nonnullable draft outcome is provisional, never a settled rejection.
- `src/store/case_store.py`: triggered proposals become pending_review through the existing validated write/log mechanism; untriggered proposals retain existing status behavior. Proposal log text must explicitly avoid a final-decision impression.
- `src/api/__init__.py`: render proposal status and review reasons prominently, without presenting provisional outcome/remedy/amount as final or suggesting money moved. Tolerate proposal confidence being absent; escape dynamic text. Preserve final result display.
- `tests/test_demo_app.py`, `tests/test_judge.py`, `tests/test_case_store.py`: add focused integration and regression coverage. Existing test helpers are in tests/cases.py and tests/builders.py. Use eval labels only in tests if helpful; no need to modify labels except replacing DISP-004's obsolete universal-replay caveat with an accurate runtime/test separation note.

If an exact location differs, find its current equivalent before editing; retain the specified behavior.

## Tasks & Acceptance

- [x] Add source-grounded 003/004 scripts and route each Case to its dispute's replies with no wildcard fallback.
- [x] Add minimal review triggers, pending state and clear proposal display/log text; preserve 002 behavior and untriggered proposal lifecycle.
- [x] Cover every matrix row and rerun the Python test suite.

Given DISP-003, when the demo runs, then both submissions concern its four-minute wait and the final reversal equals the fare cancellation fee and calculation result.

Given DISP-004, when the demo runs, then both submissions acknowledge the GPS gap, its balanced-evidence trigger is recorded, its stored status is pending_review and its page says no final decision. No Outcome/payment is created.

Given repeated or interleaved runs, when stored pages are reopened, then responses and citations remain attached to the correct dispute and no model rerun occurs on a page read.

## Spec Change Log

- 2026-10-12: Functional scope approved by the user's case-specific replies and review-pending confirmation. Preserve all unrelated staged and unstaged work; no push.

## Verification

Run focused demo/Judge/store/page tests, then `uv run --locked pytest -q tests`. Record counts, matrix coverage and relevant limitations here. Use `git diff --check` on task files. No network model is needed. Do not stage or commit files; the parent handles final review and presentation.

- 2026-10-12 implementation verification: focused demo/Judge/store/page tests **50 passed**; full `uv run --locked pytest -q tests` **148 passed**. Both runs emitted the existing Starlette TestClient/httpx deprecation warning.
- Matrix coverage: final DISP-002 reject/no_action; final DISP-003 uphold/fee_reversal with fare-derived SGD 5.00 and matching calculation; DISP-004 balanced-evidence proposal pending review with no Outcome/payment authorization; mixed order 004/003/002/004 with independently stored submissions, citations, sealed evidence and pages; unknown prepared script raises ModelError; configured low-confidence threshold including boundary and combined triggers; catalog/replay reads reject any *.eval.json file. Additional coverage verifies independent list replies and escaped proposal text with absent confidence.
- `git diff --check` passed for task files. DISP-002 fixture is unchanged; preexisting staged/unstaged edits were preserved. uv's sandbox interpreter cache initially failed with Access denied; the approved escalated test runs succeeded. No network model, staging, commit or push was used.
- Remaining scope limitation: proposals require human review, but this fix does not implement a review service or authorize payments. DISP-004 retains a required nonnullable provisional draft outcome internally; its page and ruling log explicitly state that no final decision was made.
- 2026-10-12 review test patches: dedicated Review reasons list assertions now verify the stored trigger and escaped reason within that list; missing-agent scripts must raise a dispute/agent-specific ModelError without fallback; both low-confidence and balanced-evidence uphold/fee_reversal proposals retain fare-derived amounts and matching calculations while pages and ruling logs require review without a final Outcome/Amount display or payment authorization. Runtime behavior and frozen intent were unchanged. Focused demo/Judge/store/page tests **55 passed**; full `uv run --locked pytest -q tests` **153 passed**; existing Starlette TestClient/httpx warning only. Scoped `git diff --check` passed.

- Independent review: edge-case review found no defects. Verification review exposed a page-wide assertion that could pass using log text; assertions now target the dedicated review list. Added missing-agent and proposed-fee-reversal coverage. Final focused checks: **55 passed**; full suite: **153 passed**. No runtime changes were required after review. Other suggested expansions were outside this approved demo fix or already covered by existing behavior.

## Suggested Review Order

Integration note (2026-10-12): before pushing, merged `origin/main` at `e697d7f`, which adds argument-reference validation, Judge self-checks, History processing and party notifications. Preserved the case-specific replay and provisional display while adapting fixtures and tests to those contracts. DISP-004 now uses main's named GPS policy gap, computed confidence 0.5, and balanced-evidence/policy-gap/low-confidence triggers. Final cases reach `notified`; review proposals send pending-review notices without authorizing payments. The combined suite passed **211 tests**, with **one preexisting expected failure** concerning DISP-002's post-History confidence. The original working folder and its pending changes were preserved using a separate integration checkout.

**Case-specific replay**

- Resolve each script from the stored dispute, independent of Case numbering.
  [demo.py:21](../../src/api/demo.py#L21)

**Prepared case arguments**

- Ground the early-cancellation arguments in the four-minute wait and recorded rider reply.
  [DISP-003.json:1](../../fixtures/stub/DISP-003.json#L1)

- Represent the GPS gap as unresolved and request human review.
  [DISP-004.json:1](../../fixtures/stub/DISP-004.json#L1)

**Review boundary**

- Turn balanced or low-confidence drafts into proposals using existing calculated confidence.
  [__init__.py:94](../../src/agents/judge/__init__.py#L94)

- Store triggered proposals as pending review and record an explicitly provisional log entry.
  [case_store.py:175](../../src/store/case_store.py#L175)

- Display review reasons without exposing a final outcome or payable amount.
  [__init__.py:63](../../src/api/__init__.py#L63)

**Regression coverage**

- Verify mixed runs, fare-derived reversals, citation integrity and stored-page stability.
  [test_demo_app.py:39](../../tests/test_demo_app.py#L39)

- Keep evaluation labels outside catalog and replay runtime reads.
  [test_demo_app.py:135](../../tests/test_demo_app.py#L135)

- Verify pending refund calculations and the dedicated review-reasons list.
  [test_page.py:85](../../tests/test_page.py#L85)
