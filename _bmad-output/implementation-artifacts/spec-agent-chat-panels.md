---
title: Backend-protected agent Communication Log panels
type: feature
created: 2026-10-12
status: done
baseline_commit: 620f27822e9b6925a5b123d0f7a1bb4232508d49
review_loop_iteration: 0
context:
  - AGENTS.md
  - GLOSSARY.md
  - docs/architecture.md
  - docs/adr/0001-history-withheld-from-judge.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Show recorded agent collaboration as chat-style Communication Logs in both apps. The user approved both surfaces and code **482731**, then explicitly approved **backend validation and backend-served messages for the Rider prototype too**, replacing the browser-only gate. Both apps start locked, unlock on the server, and can Lock again.

## Boundaries & Constraints

Always preserve public summaries, citations, timestamps and event order. Explain Case store handoffs; Advocates never directly chat. Rider execution includes only three Rider agents and Application; backend evidence/policy functions are code tools. Keep case results, original reports, source scope and workflows unchanged. Case data is simulated and client-originated Rider activity is not authenticated evidence.

Server validation must precede transcript retrieval. No access code or unlock flag in frontend source/session storage, URLs, logs or cookies. Use opaque expiring/revocable HttpOnly SameSite sessions. Do not persist Rider transcript messages in browser case storage; store a server handle instead. Existing old cases may upload their recorded log once and replace it with a handle. Keep public case content available when chat service fails; show a truthful retry/recovery path. No third-party service, dependency, new model calls, fabricated dialogue, private reasoning, Judge/policy rule changes, or unrelated edits. Ask before remote Git operations or broader pipeline integration. This remains a local demo, not production identity/security.

## I/O & Edge-Case Matrix

| State/input | Expected behavior |
| --- | --- |
| Initial or wrong/blank code | Locked password form; no transcript DOM/API data; accessible error for denial |
| Correct code | Server grants opaque session; fetch selected report/case transcript and actual actors |
| Filter / All activity | Subset / original order without rerunning agents |
| Lock / expiry / restored page | Remove displayed messages, revoke or recheck authorization; no stale restored transcript |
| Other client / unknown handle | No access to protected transcript; clear 403/404 |
| Older stored Rider case | Upload existing recorded log, save handle without messages; no invented recipients |
| Backend unavailable / restarted / storage denied | Fail closed; case/report content survives; explicit retry/reprepare path, no browser-only fallback |
| Rejected/unsupported/review case | Only actual activity; no fictional response or final review decision |
| HTML-like text | Text rendering, escaped server HTML; never executable markup |

</frozen-after-approval>

## Code Map

- Existing task edits already add chat UI in `prototypes/shared/agent-chat.js`, `prototypes/shared/rider-case.css`, `prototypes/ryde-app/rider-case-panel.js` and both HTML entry points. KEEP styling, filters, safe text rendering and cache-versioned assets. Replace the browser access object/code/flag with a backend client; exports may change and tests must follow. Unknown actors retain truthful recorded-activity labels.
- `src/api/chat.py` has ChatAccess, 30-minute sessions, safe backend HTML, routes/citations. KEEP server gate/tests. Add an app-local Rider transcript repository and API registration/read/unlock/lock with bounded payloads and retention; upload only public log and minimal rider/trip/report context. Handle must be opaque and retrieval protected. Share code validation/session mechanism with backend case pages. Do not claim a Human Reviewer queue executes; use review-routing context.
- `src/api/__init__.py` wires case routes and `RYDE_CHAT_ACCESS_CODE` (default 482731, explicit empty fails closed). Wire Rider API and serve `prototypes/` using FastAPI static routes after API routes, preserving `/` as Prepared Disputes and current `/ryde-app/`, `/ryde-report/`, `/index.html` asset paths. One same-origin uvicorn server should serve both apps; no CORS or separate static server required. Protected responses use no-store. Keep 404 and no-model-call GET behavior.
- `prototypes/ryde-app/report-case.js`, `rider-case-panel.js`, `rider-case-store.js`: register newly prepared public logs before saving browser cases; persist handle and empty/absent log, never raw transcript. Migrate old stored logs when opened; preserve report snapshot checks and save errors. Pipeline algorithms remain read-only. Case JSON export is disabled while locked and fetches authorized current transcript before download; do not rely on a cached authorization boolean. Handle backend restart through explicit reprepare, never silent reruns.
- Shared client must discard message copies on Lock, authorization failure and page restoration; handle stale async requests so late responses cannot repopulate a locked/replaced panel. Existing report reset/trip switching must remain scoped. Do not send original report/media/full evidence to the transcript endpoint.
- Update `tests/test_chat.py`, backend page/demo tests, `prototypes/ryde-app/tests/agent-chat.test.cjs` and focused integration tests. Existing pipeline tests stay valid. README/prototype instructions must use backend startup, explain in-memory transcript lifetime and demo limitations, remove browser-only code configuration claims.

## Tasks & Acceptance

- [x] Replace Rider browser gate with backend transcript registration, protected retrieval and safe persistence/recovery.
- [x] Serve both apps with one backend; preserve case-page gate and add Rider APIs.
- [x] Test matrix including server denial, browser redaction, stale requests, export, expiry/revocation and existing regressions; update docs.

Both Rider entry points must use the same backend gate. A correct code entered in the Rider app must cause server validation before messages are returned. Locked API responses must contain no log summaries/references. Browser saved cases must retain only the transcript handle, while case content and original report remain intact.

## Spec Change Log

- 2026-10-12: User approved both app panels and demo code 482731. Current branch fast-forwarded to the tested main integration while preserving pending local edits. No push requested for this feature.
- 2026-10-12: User explicitly replaced the browser-only Rider gate with backend validation and backend-served transcripts. Revised persistence/hosting/API boundaries; KEEP existing chat design, actual-agent scope and server case gate. Earlier browser-gate verification is superseded for Rider access.

## Verification

Run complete Python tests and all four Node prototype suites. Each matrix row needs a passing automated check; browser-test both Rider entry points and backend locked/wrong/unlock/filter/Lock/reopen. Previous implementation baseline: Python 232 passed, 1 existing xfail; Node 27 passed. Phone viewport override did not affect actual browser width; disclose if this remains unavailable. Do not invoke a nested skill, stage, commit, push or run reviews; parent owns the BMad workflow.

### Results

- Full regression: Python **256 passed, 1 existing xfail**; Node **33 passed**. Existing Starlette/httpx deprecation warning only.
- API and DOM contract tests cover every matrix row, including expiry, revoked-cookie replay, client separation, bounded retention, older-case migration, storage/backend failure, safe text, late responses, report reset and protected export.
- Browser: one uvicorn server on port 8889 serves both apps. Older saved Rider case migrated without rerunning agents; newly filed DISP-004 report registered its own log. Initial/wrong-code lock, correct unlock, actor/All activity filter and Lock/reload passed. Backend DISP-004 remains a proposal pending review. Backend Lock followed by Rider JSON export returned a denial, removed messages and disabled export.
- A true narrow-screen browser check remains unavailable: viewport override did not change actual browser dimensions. Responsive scoped styles were inspected.

## Integration & Review

- 2026-10-12: Fetched `origin/main` at `620f278`; `git merge --ff-only origin/main` reported already up to date. No incoming conflicts or changes. User instructed that main's changes remain intact; patches are limited to the new chat feature, its direct UI integration and tests. Core agent algorithms, policies and Rulings remain unchanged.
- All three independent review layers completed. Deduplicated findings are patches within the approved feature; no new product decisions or pre-existing issues were deferred.

| Finding | Consequence | Route |
| --- | --- | --- |
| Legacy migration loses original events on failed upload or repeats completed uploads | High: historical activity loss | Patch |
| Report recovery drops its report-save requirement | Medium: saved case cannot reopen | Patch |
| Hung backend registration blocks usable public case | Medium: no recovery controls | Patch |
| Concurrent first registrations or unlocks lose browser access | Medium: valid records become inaccessible | Patch |
| Stale unlock cleanup revokes a newer panel session | Medium: incorrect access denial | Patch |
| Other open tabs retain messages after Lock | Medium: stale visible activity | Patch |
| Transcript lifetime exceeds retention deadline in the UI | Medium: stale visible activity | Patch |
| Invalid Unicode payload/code or owner cookie causes server error | Medium: unhandled failure | Patch |
| Inherited actor names break filters | Low: mislabeled activity | Patch |
| Lock and denial remove keyboard focus | Low: keyboard navigation interrupted | Patch |
| Backend expiry, actual export artifact and reset listener lack executable integration assertions | Medium: regressions can escape | Patch |

Legacy migration must leave pre-existing storage untouched after failed upload and retry the original activity; it must never write raw activity anew. Successful registration replaces the legacy record with a server handle, even if its panel was closed. New report reset still cancels obsolete saves.

## Suggested Review Order

- Inspect server validation, owner-scoped transcripts and revocable unlock sessions.
  [chat.py:21](../../src/api/chat.py#L21)

- Follow locked rendering, authorized retrieval and stale-request guards.
  [agent-chat.js:185](../../prototypes/shared/agent-chat.js#L185)

- Verify ownership, denial, expiry and Rider transcript protection.
  [test_rider_chat.py:35](../../tests/test_rider_chat.py#L35)
