# Waypoint ride-hailing and Rider Evidence Agent prototype

Start at `prototypes/index.html`. The app is at `/ryde-app/`, with ride planning first, recent trips below and optional support at `/ryde-report/`. Waypoint uses a charcoal, white and blue editorial visual style with a locally hosted rounded font, custom route logo and Pip mascot. Ride requests, driver matches, fare estimates and 3D trips are simulations. No real ride is booked and there is no official Ryde integration.

## Ride hailing experience

1. Choose a pickup, drop-off and ride type. The estimated fare and journey time adjust to the selected route.
2. Choose **Find my ride** for a clearly labelled sample driver match.
3. Choose **Follow the pickup** to open the CSS 3D trip scene, where one steady overview shows the rider, driver, route and car from match to arrival. Play, pause, scrub the route or jump between trip moments without changing the camera.
4. Scroll through the landing page to see the trip, conversation and support scenes reveal as they enter view. Reduced-motion preferences and keyboard navigation are supported.

## Optional support and evidence flow

1. Select Michael Wong's cancelled DISP-002 trip, or his invented route-deviation trip.
2. Inspect Overview, Receipt, and Messages.
3. Open Rider evidence and choose **Collect rider evidence**. Expand items or the Communication log, or download the evidence JSON.
4. Choose **Report an issue** in Overview. The existing report form opens with the selected rider and trip. Enter your own statement, add optional files/photos, review, and create a demo report.
5. Creating a confirmed Rider report automatically prepares a local Rider case: Evidence Agent → Policy Agent → Rider Advocate. Inspect the arguments, counter-evidence, missing information, full policy references and communication log below the report result.
6. Choose **View in the Rider app**, or open **Your case** for the selected trip. The report and prepared case use this tab's session; download either JSON to retain a copy. Older saved reports can use **Prepare Rider case** in the app.
7. Switch to Aisha Tan's demo account to see a separate trip and evidence scope.

## Rider case studio

This side feature uses predefined JavaScript rules, not a live model. It runs step 3 evidence collection, step 4 policy retrieval and step 5 preparation of the Rider's strongest supported review request. The Rider's report is preserved verbatim; Driver messages, missing GPS, metadata-only attachments, and policy limits remain visible. The review preview retains five policy matches; case extraction includes every matching Rider clause.

Case building is configured for no-show/cancellation and route deviation. Other categories produce a support-routing message without an Advocate Submission or active Case. Secondary safety wording is flagged for human review; this demo does not contact support. Unknown Trips and wrong roles cannot be substituted into a case.

The result is a Rider-only Submission draft, not the complete shared Case pipeline. Its in-memory evidence snapshot contains Rider-visible app records; the feature does not create a Driver Submission, seal the full shared evidence set, run the Judge, issue a Ruling, or process payment. Session data is client-editable and is not authenticated evidence. Failed/stale session saves are reported explicitly.

Run the existing evidence checks and new case-flow checks with `node --test prototypes/ryde-app/tests/*.test.cjs` from the repository root (or pass the two test filenames explicitly on shells without glob expansion).

## Data boundaries

- The collector is deterministic JavaScript with source-labelled Evidence Items, explicit available/missing status, and real collection events. It makes no LLM or network calls and produces no Ruling.
- `data.js` provides a rider-visible subset of DISP-002 and two clearly labelled invented fixtures. It does not include driver-private telemetry, driver history, expected rulings, or the evaluation summary.
- Rider-visible conversations can include incoming driver messages. This does not grant access to private driver records.
- DISP-002 contains no rider-device location data. Its driver GPS must never be relabelled as rider GPS. The route fixture has only two invented rider-device samples, insufficient to establish an actual route.
- `rider-evidence-agent.js` validates trip ownership before reading sources. Changing account or trip invalidates the displayed collection. The report must match the selected trip and have the Rider role.
- Confirming **Create demo report** for a known Rider trip saves its text, media metadata, and prepared case in sessionStorage under rider-and-trip-specific keys. The original manual save action remains available for retrying report storage. Nothing is sent to Ryde. Actual media bytes remain in the form's memory and are not transferred; their evidence items are marked missing / metadata-only.
- Session records are client-editable demo data, not authenticated records. Production requires server-side identity, authorization, storage and upload APIs. The browser's account selector is only a demonstration of scope filtering.
- Both apps should use the same localhost origin for reliable session transfer. Browsers may isolate file-URL storage or block it; save/read failures appear visibly. JSON downloads still provide a local export.

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
- `rider-evidence-agent.js`: evidence collection and communication events.
- `rider-policy-agent.js`: capped review preview and full Rider policy extraction.
- `rider-advocate-agent.js`, `rider-case-pipeline.js`: deterministic Rider argument preparation and ordered handoffs through a local in-memory case store.
- `rider-case-store.js`, `rider-case-panel.js`, `report-case.js`, `../shared/rider-case.css`: report-bound session persistence, reusable case display, report-created integration and styling.
- `session-store.js`: optional report session storage.
- `report-bridge.js`: selected-trip prefill and explicit save action in `../ryde-report/index.html`.

The booking preview, fares, driver, route animation and messages are all local simulations; requesting a ride does not create a booking. The 3D scene is illustrative rather than live GPS or a data source for the Rider Evidence Agent. The project workflow, shared Python contracts and production application are not modified by this prototype. The local Rider Advocate uses templates; a production advocate and Judge remain separate implementation work.
