# Waypoint ride-hailing and Rider Evidence Agent prototype

From the repository root, run `uv run uvicorn src.api.demo:app`, then open `http://127.0.0.1:8000/index.html`. The same backend serves the app at `/ryde-app/`, with ride planning first, recent trips below and optional support at `/ryde-report/`. `/` remains the Prepared Disputes demo. Both Rider entry points need this backend; FastAPI is mandatory for all Rider agents, policy preview and Communication Logs. A separate static server or file URL cannot execute the agents. Waypoint uses a charcoal, white and blue editorial visual style with a locally hosted rounded font, custom route logo and Pip mascot. Ride requests, driver matches, fare estimates and 3D trips are simulations. No real ride is booked and there is no official Ryde integration.

## Ride hailing experience

1. Choose a pickup, drop-off and ride type. The estimated fare and journey time adjust to the selected route.
2. Choose **Find my ride** for a clearly labelled sample driver match.
3. Choose **Follow the pickup** to open the CSS 3D trip scene, where one steady overview shows the rider, driver, route and car from match to arrival. Play, pause, scrub the route or jump between trip moments without changing the camera.
4. Scroll through the landing page to see the trip, conversation and support scenes reveal as they enter view. Reduced-motion preferences and keyboard navigation are supported.

## Optional support and evidence flow

1. Select Michael Wong's DISP-002 trip, or choose **Demo rider R-7824** for DISP-003 and **Demo rider R-7825** for DISP-004 in the Rider profile selector. Michael also has DISP-005, DISP-006 and DISP-007 plus the original sparse route example.
2. Inspect Overview, Receipt, and Messages.
3. Open Rider evidence and choose **Collect rider evidence**. Expand items or the Communication log, or download the evidence JSON.
4. Choose **Report an issue** in Overview. The report form opens with the selected rider and trip. Choose **Load DISP-003 report example** or **Load DISP-004 report example** to populate that trip's report, or write your own statement. Add optional files/photos, review, and create a demo report. From the standalone report page, use **Choose an example** and **Load sample report** for any of the six reports.
5. Creating a confirmed Rider report automatically prepares a local Rider case: Evidence Agent → Policy Agent → Rider Advocate. Inspect the arguments, counter-evidence, missing information and full policy references below the report result. Unlock the Communication Log with **482731** to see recorded activity, filter by actor, or choose **Lock** to hide it again.
6. Choose **View in the Rider app**, or open **Your case** for the selected trip. The report and prepared case use this tab's session; download either JSON to retain a copy. Older saved reports can use **Prepare Rider case** in the app.
7. Switch to Aisha Tan's demo account to see a separate trip and evidence scope.

## Rider case studio

This side feature executes deterministic Python rules in `src/agents/rider/`, without model calls. JavaScript is a presentation/API adapter with no rules fallback. It runs step 3 evidence collection, step 4 policy retrieval and step 5 preparation of the Rider's strongest supported review request. The Rider's report is preserved verbatim; Driver messages, missing GPS, metadata-only attachments, and policy limits remain visible. The review preview retains five policy matches except Route Deviation, which always preserves the four baseline clauses. Case extraction includes every matching Rider clause and the Route Deviation Driver baseline clauses, using the existing shared policy JSON and its richer title/category/keyword metadata.

Case building is configured for no-show/cancellation and route deviation. Other categories produce a support-routing message without an Advocate Submission or active Case. Secondary safety wording is flagged for human review; this demo does not contact support. Unknown Trips and wrong roles cannot be substituted into a case.

The result is a Rider-only Submission draft, not the complete shared Case pipeline. Its in-memory evidence snapshot contains Rider-visible app records; the feature does not create a Driver Submission, seal the full shared evidence set, run the Judge, issue a Ruling, or process payment. Session data is client-editable and is not authenticated evidence. Failed/stale session saves are reported explicitly.

The Communication Log is shared by the report result and the app's **Your case** tab. It shows only recorded Rider Evidence, Rider Policy, Rider Advocate and Application activity, with timestamps, event kinds and citations. The local case store coordinates handoffs; advocates do not chat directly. Actor filters read the existing log without rerunning the pipeline. Unsupported categories show only their recorded Application events.

Code validation and message retrieval use the backend gate shared with prepared Case pages. Configure `RYDE_CHAT_ACCESS_CODE` on the server (default **482731**); an explicitly empty value disables unlocking. The browser contains no configured code or saved unlock flag. Opaque HttpOnly SameSite cookies bind logs to the browser that registered them and grant access for 30 minutes. **Lock** immediately removes displayed messages and revokes the server access session across both apps. A restored page starts locked. Case JSON export fetches the current authorized log before download; expired or revoked access clears displayed activity. The separate report download remains available.

The Python case endpoint registers its actual generated public activity plus minimal scope IDs in `RiderTranscripts`, sets the owner cookie, and returns only the opaque handle with both activity arrays redacted. Standalone evidence uses the same locked presentation and authorized export. Saved cases retain a server handle and empty activity arrays (including the evidence bundle’s log); original reports and case results stay intact. Older saved cases upload their existing events once when opened, without rerunning agents or inventing recipients. The legacy client-log upload endpoint remains for old saved cases only. The server retains public logs in memory for six hours with 1,000-record/16 MiB repository limits; legacy uploads are limited to 256 KiB. They are simulated and are not authenticated evidence. Use one backend process; restarting it clears transcripts and sessions. A missing or expired handle offers explicit **Prepare Rider case again**, never a silent pipeline rerun.

The report is saved before the Python request. Backend outages preserve that report and show a visible retry error; they cannot run agents locally. Existing public case content remains available, while messages and case export stay locked. Retry access after a temporary outage, or explicitly prepare again after a restart. Storage denial is shown visibly; a newly prepared case can still be read in page memory and its log unlocked on the backend, then exported while authorized. This remains a local demo, not production identity/security.

Requests, including response parsing, time out after ten seconds. Cookie-changing Rider requests queue in the page and use same-origin Web Locks across tabs where available. Browsers without Web Locks only serialize within each page. Lock and denial send a fixed invalidation signal through BroadcastChannel to hide other open logs; returning to a tab clears its displayed log and requires fresh code entry. No messages, codes or unlock flags are stored for this coordination.

An older case whose migration fails keeps its pre-existing browser record untouched, including its historical log. This temporary migration exception prevents losing recorded events during an outage; the displayed case is redacted, and explicit retry uses the original page-memory snapshot without rerunning agents or changing timestamps. Successful registration replaces that legacy record with the scoped handle and empty log arrays, even if its panel was closed while the request completed, provided the saved report/case has not changed.

Run Python agent/API behavior checks with `.venv/Scripts/python.exe -m pytest -q tests` (Windows may require execution outside the sandbox for local test-client sockets), and UI/API adapter, sample/store and chat checks with `node --test prototypes/ryde-app/tests/*.test.cjs` from the repository root (or pass `evidence.test.cjs`, `rider-case.test.cjs`, `samples.test.cjs` and `agent-chat.test.cjs` explicitly on shells without glob expansion).

## Data boundaries

- The Python collector emits source-labelled Evidence Items, explicit available/missing status and public collection events. It makes no model calls and produces no Ruling. Browser requests time out after ten seconds, show errors and discard stale results after trip changes or disposal.
- `data.js` provides rendering and synchronous selection only. Python reads the corresponding curated public catalog under `data/prototype/`, including DISP-002–007 and both existing invented fixtures. The catalog was extracted once with Node; `scripts/build_route_samples.py` keeps both route projections synchronized, and parity tests prevent drift. It does not include driver-private telemetry, driver history, expected rulings, or evaluation labels. The Rider case feature prepares a review request; loading a sample does not force a ruling or refund.
- Rider-visible conversations can include incoming driver messages. This does not grant access to private driver records.
- DISP-002 contains no rider-device location data. Its driver GPS must never be relabelled as rider GPS. The route fixture has only two invented rider-device samples, insufficient to establish an actual route.
- `src/agents/rider/evidence.py` validates simulated Rider/Trip ownership before reading trusted sources. Changing account or trip invalidates the displayed collection. The report must match the selected trip and have the Rider role.
- Confirming **Create demo report** for a known Rider trip saves its text, media metadata, and public case content in sessionStorage under rider-and-trip-specific keys, with only a backend transcript handle for recorded activity. The original manual save action remains available for retrying report storage. Report text and metadata go to the local Python service, which reads trusted catalog telemetry and policy. Request bodies are bounded to 128 KiB and eight nesting levels; malformed nested metadata, non-finite values, Driver and cross-Rider requests are rejected visibly. Nothing is sent to Ryde. Actual media bytes remain in the form's memory and are not transferred; their evidence items are marked missing / metadata-only.
- Session records are client-editable demo data, not authenticated records. Production requires server-side identity, authorization, storage and upload APIs. The browser's account selector is only a demonstration of scope filtering.
- Both apps use the same backend origin for cookies and session transfer; no CORS or separate static server is needed. Save/read failures appear visibly. Report JSON stays downloadable; case JSON requires a current authorized backend read.

## Files

- `index.html`, `styles.css`, `app.js`, `ride-booking.js`: booking screen and local ride-request simulation.
- `../index.html`: scroll-led Waypoint landing page.
- `../shared/waypoint.css`: active shared design for every screen in both prototypes.
- `../shared/waypoint-mark.svg`, `../shared/pip.svg`: original logo and mascot.
- `../shared/waypoint-route.svg`, `../shared/waypoint-car.svg`: route and vehicle illustrations.
- `../shared/experience.css`, `../shared/experience.js`: scroll reveals, app introduction and ride request styling.
- `../shared/journey.css`, `../shared/journey.js`: independent 3D trip simulation.
- `../shared/BRAND.md`: identity, colours and asset usage.
- Earlier `redesign.css`, `theme.css` and `editorial.css` files are retained as design history and are not loaded by either page.
- `data.js`: scoped simulated app records.
- `rider-api.js`: minimal asynchronous API adapter and synchronous UI ownership selection.
- `report-policy-preview.js`: policy rendering, retry and stale-response guards.
- `../../src/agents/rider/`: Python evidence, policy, advocate, validation and ordered workflow.
- `../../src/api/rider.py`: bounded requests, server-created public logs and redacted responses.
- `../../data/prototype/rider-catalog.json`: trusted public records; no histories/evaluation labels.
- `../../src/tools/evidence/route.py`: the single route/fare calculator; the browser calculator was removed.
- `rider-case-store.js`, `rider-case-panel.js`, `report-case.js`, `../shared/rider-case.css`: report-bound session persistence, reusable case display, report-created integration and styling.
- `session-store.js`: optional report session storage.
- `report-bridge.js`: selected-trip prefill and explicit save action in `../ryde-report/index.html`.

The booking preview, fares, driver, route animation and messages are all local simulations; requesting a ride does not create a booking. The 3D scene is illustrative rather than live GPS or a data source for the Rider Evidence Agent. The project workflow, shared Python contracts and production application are not modified by this prototype. The local Rider Advocate uses templates; a production advocate and Judge remain separate implementation work.
