# Waypoint ride-hailing and Rider Evidence Agent prototype

Start at `prototypes/index.html`. The app is at `/ryde-app/`, with ride planning first, recent trips below and optional support at `/ryde-report/`. Waypoint uses a charcoal, white and blue editorial visual style with a locally hosted rounded font, custom route logo and Pip mascot. Ride requests, driver matches, fare estimates and 3D trips are simulations. No real ride is booked and there is no official Ryde integration.

## Ride hailing experience

1. Choose a pickup, drop-off and ride type. The estimated fare and journey time adjust to the selected route.
2. Choose **Find my ride** for a clearly labelled sample driver match.
3. Choose **Follow the pickup** to open the CSS 3D trip scene, where you can watch the car approach, pause, scrub the route, jump between trip moments, and switch rider/driver viewpoints.
4. Scroll through the landing page to see the trip, conversation and support scenes reveal as they enter view. Reduced-motion preferences and keyboard navigation are supported.

## Optional support and evidence flow

1. Select Michael Wong's cancelled DISP-002 trip, or his invented route-deviation trip.
2. Inspect Overview, Receipt, and Messages.
3. Open Rider evidence and choose **Collect rider evidence**. Expand items or the Communication log, or download the evidence JSON.
4. Choose **Report an issue** in Overview. The existing report form opens with the selected rider and trip. Enter your own statement, add optional files/photos, review, and create a demo report.
5. Choose **Save demo report to rider app**, then **Return to rider evidence**. Collect again to include the report and declared attachment metadata.
6. Switch to Aisha Tan's demo account to see a separate trip and evidence scope.

## Data boundaries

- The collector is deterministic JavaScript with source-labelled Evidence Items, explicit available/missing status, and real collection events. It makes no LLM or network calls and produces no Ruling.
- `data.js` provides a rider-visible subset of DISP-002 and two clearly labelled invented fixtures. It does not include driver-private telemetry, driver history, expected rulings, or the evaluation summary.
- Rider-visible conversations can include incoming driver messages. This does not grant access to private driver records.
- DISP-002 contains no rider-device location data. Its driver GPS must never be relabelled as rider GPS. The route fixture has only two invented rider-device samples, insufficient to establish an actual route.
- `rider-evidence-agent.js` validates trip ownership before reading sources. Changing account or trip invalidates the displayed collection. The report must match the selected trip and have the Rider role.
- Saving a report is explicit. `session-store.js` stores its text and media metadata in sessionStorage under rider-and-trip-specific keys. Nothing is sent to Ryde. Actual media bytes remain in the form's memory and are not transferred; their evidence items are marked missing / metadata-only.
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
- `session-store.js`: optional report session storage.
- `report-bridge.js`: selected-trip prefill and explicit save action in `../ryde-report/index.html`.

The booking preview, fares, driver, route animation and messages are all local simulations; requesting a ride does not create a booking. The 3D scene is illustrative rather than live GPS or a data source for the Rider Evidence Agent. The project workflow, shared Python contracts and production application are not modified by this prototype. This is not a completed Rider Advocate or Judge implementation.
