---
title: Route Deviation resolved end to end
type: feature
created: 2026-10-12
status: done
baseline_commit: 6a65e99b1a02a0a9e545fe903ceb4649e3e24ed4
review_loop_iteration: 0
context:
  - AGENTS.md
  - GLOSSARY.md
  - docs/adr/0001-history-withheld-from-judge.md
  - docs/adr/0002-thresholds-come-from-trip-data-not-policy-text.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Implement Ticket 06 in backend and Rider prototypes: computed route/fare evidence, opposing arguments and three simulated resolutions using the approved refund rule.

## Boundaries & Constraints

**Always:** Preserve main's console, No-Show behaviour and local chat/BMad work. Keep R-04, D-04, R-03, D-03 unchanged; record ADR 0004 before code. Preserve sealed evidence, independent Advocates, citation repair, post-outcome History and review safeguards. Rider prototypes present Submissions, not Judge decisions. All agent and route/fare logic runs in Python; retain the existing HTML/CSS web interface and JavaScript for presentation and API calls only (human-approved amendment, 2026-10-12).

**Ask First:** Changes to the approved refund rule, shared contract fields, policy wording or unrelated features; remote Git operations.

**Never:** Use evaluation labels at runtime, infer consent/fault from distance, invent telemetry, mislabel vehicle GPS as Rider GPS, execute payments or add external services.

## I/O & Edge-Case Matrix

| Scenario | Expected behaviour |
| --- | --- |
| DISP-008: unsupported excess route; full-fare refund requested | Rider wins a smaller, code-computed partial refund |
| DISP-009: matching Rider-requested detour in chat | Driver Advocate cites exact request; claim rejected, no refund |
| DISP-010: unclear consent/explanation | Balanced proposal pending review; no authorised amount |
| Missing/invalid route, tariff, surge or promo | Explicit unavailable evidence; no guessed refund; review |
| Stationary jitter, endpoints, telemetry gaps | Bounded stop candidates; no invented dwell or purpose |
| Original two-endpoint prototype route | Insufficient-path limitation retained |
| Existing No-Show cases | Existing results, thresholds, binary remedies and known xfail unchanged |

</frozen-after-approval>

## Code Map

- `src/tools/evidence/__init__.py:16`: category dispatch to new `route.py`; preserve cancellation helpers. `src/intake/catalog.py:37` excludes `.eval.json` already.
- `src/agents/policy/__init__.py:27`, `src/config.py:82`: clauses/remedies/checklist. `src/agents/judge/{draft,numbers,__init__}.py`: monetary validation, partial-outcome burden and amount calculation. Keep contracts unchanged. `src/agents/prompting.py`: route metrics without raw polylines or History.
- `src/agents/advocates/__init__.py:21`, `src/agents/outcomes.py:37`, `src/orchestrator/__init__.py:23`: category guidance/support/wording. Six advocate Markdown documents have local route notes; preserve and align with implemented sources/ADR.
- `src/api/demo.py:18`, `src/api/__init__.py` `_dispute_row`, `src/api/static/console.js`: additional cases and route-specific fare/calculation/partial/pending display; preserve upstream APIs/design/chat. Add new recordings in `src/api/static/recorded/`; leave old recordings intact.
- `prototypes/ryde-app/data.js:274`, `prototypes/ryde-report/index.html` `loadSample`: curated projections/category selection. Python Rider agents plus `rider-api.js`: evidence-sensitive arguments and four-clause baseline; retain ownership, reports and chat lifecycle.
- `src/agents/rider/{evidence,policy,advocate,validation}.py` and `__init__.py`: Python Rider rules and workflow 3 → 4 → 5. `src/api/rider.py` serves bounded case/evidence/policy-preview endpoints and creates locked server logs. `data/prototype/rider-catalog.json` is the trusted public catalog; `src/tools/evidence/route.py` is the sole calculator. `prototypes/ryde-app/rider-api.js` and policy/app/panel renderers make async API calls only. Keep `TRIP-DEMO-ROUTE-01` insufficient; exclude histories/evaluation labels.

## Tasks & Acceptance

**Execution:**

- [x] `docs/adr/0004-route-deviation-refund-rule.md`, `docs/contract-decisions.md` — record rule and analysis assumptions first.
- [x] `data/cases/disp-008..010.json`, separate `.eval.json`, `fixtures/stub/DISP-008..010.json` — create three grounded scenarios and case-specific public scripted replies.
- [x] Backend paths above — compute evidence, serve clauses, validate/calculate Rulings and extend prepared replay/console.
- [x] Prototype paths above and six agent documents — expose the cases and evidence-sensitive Rider arguments; preserve existing features.
- [x] `tests/test_route_deviation.py`, existing affected backend tests, prototype route/sample tests — exercise matrix and regressions.

**Acceptance Criteria:**

- Given raw route records, when gathering evidence, then computed distances/stops/duration and complete fare breakdown are citable with provenance.
- Given valid pricing, when awarding refund, then the Ruling shows code-recomputed amount, formula/values, ADR and input IDs.
- Given all six cases, when replaying in varied order, then labels match, consent is cited, ambiguity stays pending and No-Show/chat regressions pass.
- Given a Rider route sample, when submitting, then category, original report, four clauses, evidence and honest counterarguments stay scoped.

## Spec Change Log

- 2026-10-12: User approved the concrete specification; implementation started.
- 2026-10-12: Rule/surfaces approved. Main `6a65e99` pulled, local changes restored; integration: 86 Python/45 Node passed. Chat is separate; upstream console API stays unchanged.
- 2026-10-12: User requested all Rider agent logic in Python while retaining the web interface, and authorised the completed integration to be pushed to main.
- 2026-10-12: Pulled main through `1ce36a0`, preserving its Safety, routing, precedent, stability, evaluation and Evidence Agent features. User approved renaming the new Route Deviation cases to DISP-008–010 because main owns DISP-005–007. Main's updated History tests supersede the earlier expected-failure baseline.

## Design Notes

ADR: `optimal_net=max(0,(base+optimal_km*km_rate+expected_minutes*minute_rate)*surge+booking+tolls-promo)`; `refund=min(paid_net,max(0,paid_net-optimal_net))`. Receipt is authoritative; tariff must reconcile; no missing defaults. Decimal money; final SGD cents half-up; consistent documented distance/time precision.

Optimal is a supplied simulated road baseline. Stops: clusters within 25m for at least 120s; exclude endpoint dwell within 50m; never bridge known gaps. Preserve exact Rider request text/IDs; consent covers only its evidenced detour. Computed excess never automatically establishes entitlement.

## Verification

- `.venv/Scripts/python.exe -m pytest -q tests` — all pass, including main's current History, Safety and switch regressions.
- `node --test prototypes/ryde-app/tests/*.test.cjs` — all pass, including UI/catalog/API adapter parity and existing chat tests. Python owns all arithmetic and agent behavior tests.
- Browser: run all six console cases; inspect partial calculation, consent and pending review. Load/submit three Rider route samples; check original details and chat lock. Replay new recordings; preserve old files.

## Verification Results

- Final integrated backend: **645 passed**, including Rider behavior/API/chat, all nine prepared cases, review decisions, Safety, routing, Evidence Agents, stability and recordings for every switch combination. One third-party Starlette deprecation warning remains.
- Final interface tests: **44 passed**, covering API adapters, shared catalog parity, source ownership, async request disposal, original report storage and the chat lock lifecycle.
- Browser after the latest pull and renaming: DISP-008 returns SGD 5.39 with ADR/input citations; DISP-009 rejects using the exact Rider request; DISP-010 remains pending with no amount. Rider reports DISP-008 and DISP-010 run Python agents and preserve the original full-fare request. Backend code unlock and Lock both work. Earlier browser checks covered Driver-consent Rider behavior and saved-case handoff before renaming; automated tests cover all six Rider samples after renaming.
- Refreshed only the 48 new Route Deviation recordings (16 switch combinations per case). Main's DISP-002–007 datasets, labels, scripted replies and recordings remain unchanged.
- Verified screenshot: `route-deviation-disp008-python.png` in this task's visualization directory.

## Approved Python amendment — implementation handoff

User explicitly chose: all Rider Evidence, Policy and Advocate logic in Python; keep current web interface. Finish the current Ticket 06 implementation with this amendment. Preserve all existing local chat work and upstream console behaviour. Do not invoke the BMad renderer/workflow again; this is the resumed implementation handoff. Do not perform Git mutations or network operations. Do not make changes unrelated to this conversion. Existing Ticket 06 Python backend is implemented and tested; reuse its route analysis and shared policy JSON.

- [x] Port the complete existing `rider-evidence-agent.js`, `rider-policy-agent.js`, `rider-advocate-agent.js`, and `rider-case-pipeline.js` deterministic rules to `src/agents/rider/` Python modules. Maintain exact report preservation, selected Rider/Trip ownership, supported categories, media-metadata-only limitations, source IDs, review flags, consent/correction handling and workflow 3 → 4 → 5. No model calls are required for this local prototype. Reuse `src/tools/evidence/route.py` for all route/fare calculations, remove the duplicate browser calculator.
- [x] Create a curated JSON catalog for all current Rider app records under `data/prototype/`, excluding histories/evaluation labels. Extract the current public `RydeDemo` data once using Node. Python reads this trusted catalog, never evidence/trip data supplied by the client. Preserve UI `data.js` for trip rendering and synchronous ownership selection, which is interface logic, not agent execution. Update `scripts/build_route_samples.py` to keep the route projections in this JSON synchronized. Use the existing shared policy JSON `data/policy/waypoint-singapore-draft-2026-10.json` (inspect its richer clause metadata) rather than a second policy store; if metadata is absent use a documented synchronized projection with parity tests.
- [x] Add bounded Python API endpoints to the existing FastAPI app for Rider case preparation, evidence collection and policy preview. Keep browser API adapters minimal and asynchronous with timeout, visible errors, no browser agent fallback, and correct stale-request/disposal guards in the app/report/panel. Driver policy previews remain informational only. Do not alter current visuals. Update all call sites, script imports and cache versions. Remove executable JS agent/calculator implementations (thin API wrappers are acceptable with explicit names/comments).
- [x] Preserve the backend chat lock: Python case endpoint registers the actual generated public communication log in `RiderTranscripts`, sets its owner cookie and returns only opaque `transcript_handle` plus redacted result. Neither case nor evidence API leaks log arrays while locked (redact both `communication_log` and evidence `log`); retain the existing metadata-only original report. Evidence standalone view can show evidence records but its Communication Log should use the same backend-gated presentation. Existing client-log registration endpoint remains only for legacy migration. `AgentChat.prepare` must not overwrite a server-created handle with an empty log. Keep original report saved even if backend unavailable. Bound JSON size/depth, validate nested fields and finite JSON values, reject malformed/cross-rider/driver requests visibly; do not execute user text. No production-auth claim: Rider selector is simulated identity.
- [x] Port real agent behaviour tests from Node to Python, preserving regression coverage and all matrix rows (six samples, unsupported categories, wrong ownership, policies, metadata gaps, changed report, injection source text, withdrawal/negation, malformed nested payloads). Keep Node tests focused on UI/API adapter, store and chat lifecycle; use server-produced fixture results or a small Python subprocess test helper where appropriate instead of executing agent logic in JavaScript. Do not remove assertions merely to pass. Remove JS/Python calculator parity tests and replace with one Python source-of-truth plus API/catalog parity checks. Run `.venv/Scripts/python.exe -m pytest -q tests` and `node --test prototypes/ryde-app/tests/*.test.cjs` (Python may require escalated execution).
- [x] Update six agent MD runtime mappings, root/prototype README and ADR/spec references to describe Python-backed execution and mandatory FastAPI server; no static-only agent operation. Ensure existing No-Show and backend chat tests still pass. Report verification and any remaining risks; root will handle latest-main merge, independent review, browser check and push.

Given a confirmed report, when submitting through either web page, then Python executes all three Rider agents and the interface shows the same scoped Submission with a locked server-owned log. Given the backend is offline, then preserve the report and show retry/error without a local rules fallback. Given malicious or malformed scope/evidence inputs, then do not use client telemetry/policy or leak another simulated Rider's data. Given either route or No-Show examples, then all existing category outcomes and limitations remain intact.

## Python amendment implementation notes

- Rider rules, report preservation, ownership, policies, consent/correction handling, review flags and citations run in `src/agents/rider/`. The existing Python route/fare calculator and synchronized policy JSON are the only runtime sources.
- `data/prototype/rider-catalog.json` contains all current public app records, extracted once using Node. Route projections are synchronized by the authoring script; UI/catalog and source/API tests enforce parity.
- New bounded `/api/rider/cases`, `/api/rider/evidence` and `/api/rider/policy-preview` endpoints reject malformed/deep/non-finite payloads, client telemetry/policy, cross-Rider scope and Driver execution. Browser request/JSON timeouts and disposal guards retain the current interface.
- Python creates the actual public Communication Log in `RiderTranscripts` and returns only its opaque handle plus redacted logs. Evidence standalone uses the same gate; legacy registration exists only for migration. Cookie-changing calls share `AgentChat.transaction`. Offline preparation saves the original report and exposes retry without agent fallback.
- The executable JavaScript agents and duplicate route calculator were removed. Python behavior tests retain the six samples and edge-case matrix; Node tests cover UI/API adapters, catalog/store parity and chat lifecycle using Python-produced results for legacy fixtures.
- Latest-main integration, independent review, live browser checks and push are owned by the root task after this implementation handoff.

## Independent review and integration repairs

Three independent review layers completed before triage. All accepted findings were implementation patches within the approved intent; no product decision or spec loopback was needed.

| Finding | Severity | Route and resolution |
| --- | --- | --- |
| Disabled escalation could finalise a route refund without an amount | High | Patch: preserve recomputed money when escalation is disabled; regression added |
| Any detour request prefix could count as consent for a different observed detour | High | Patch: constrain this demo's recognised consent to the exact recorded Lavender request, landmark and stop |
| A later withdrawal could be missed | Medium | Patch: recognise withdrawal/revocation/retraction and require review |
| Serious safety words could miss a review flag | Medium | Patch: expand safety detection; regression matrix added |
| Null route records caused a crash | Medium | Patch: validate record type and mark evidence unavailable |
| Empty conversations appeared available | Medium | Patch: mark missing and hold before any authorised amount |
| Refund recomputation trusted derived route fields | High | Patch: recompute geometry and fare from sealed raw inputs; tampering regression added |
| A stop cluster could drift into the endpoint exclusion | Medium | Patch: check every cluster point; boundary regression added |
| Embedded Rider route/receipt identities could disagree with the selected trip | High | Patch: bind embedded trip and receipt to the selected public app record |
| Rider export omitted the raw inputs needed to recompute comparisons | Medium | Patch: retain curated source records without private history |
| Full-refund review and both parties' route wording lacked assertions | Medium | Patch: add classification/amount and outcome wording tests |

The new scripted route cases also supply the second Judge pass; all 48 recordings retain the expected scenario result across every switch combination. Integration checks also restored main's category-specific Safety wording, Safety escalation, SLA category set, stability confidence and category-aware outcomes. The full suite verifies these preserved behaviors alongside Route Deviation. Agent execution remains simulated; the supplied road baseline is not live routing.

## Suggested Review Order

- Start at the bounded API that executes Python agents and returns server-owned transcript handles.
  [rider.py:42](../../src/api/rider.py#L42)

- Follow Evidence, Policy and Advocate handoffs while preserving the original Rider report.
  [__init__.py:13](../../src/agents/rider/__init__.py#L13)

- Recompute route geometry, bounded stops and reconciled fares from explicit raw inputs.
  [route.py:71](../../src/tools/evidence/route.py#L71)

- Review the approved refund rule and documented demo assumptions.
  [0004-route-deviation-refund-rule.md:1](../../docs/adr/0004-route-deviation-refund-rule.md#L1)

- Keep monetary recommendations independent of model arithmetic and tampered derived summaries.
  [numbers.py:33](../../src/agents/judge/numbers.py#L33)

- Preserve main’s Safety, routing, stability and post-outcome review behavior.
  [__init__.py:48](../../src/orchestrator/__init__.py#L48)

- Keep the interface asynchronous; show backend errors without executing browser agent rules.
  [rider-api.js:40](../../prototypes/ryde-app/rider-api.js#L40)

- Verify opposing outcomes, exact consent, review safeguards and existing No-Show behavior.
  [test_route_deviation.py:33](../../tests/test_route_deviation.py#L33)

- Exercise bounded inputs, identity scope and protected transcript delivery.
  [test_rider_api.py:18](../../tests/test_rider_api.py#L18)
