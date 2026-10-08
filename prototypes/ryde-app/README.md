# Waypoint rider app and Rider Evidence Agent prototype

Open `index.html` in a browser, or serve the project's `prototypes` folder locally and open `/ryde-app/`. Waypoint uses a shared charcoal, white and blue design with the report form, inspired by Meuze's editorial style. The original route logo and Pip mascot are editable SVG assets. It is an independent simulated interface, not an official Ryde app or integration.

## Try the complete flow

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

- `index.html`, `styles.css`, `app.js`: rider interface and base layout.
- `../shared/waypoint.css`: active shared design for every screen in both prototypes.
- `../shared/waypoint-mark.svg`, `../shared/pip.svg`: original logo and mascot.
- `../shared/waypoint-route.svg`, `../shared/waypoint-car.svg`: route and vehicle illustrations.
- `../shared/BRAND.md`: identity, colours and asset usage.
- Earlier `redesign.css`, `theme.css` and `editorial.css` files are retained as design history and are not loaded by either page.
- `data.js`: scoped simulated app records.
- `rider-evidence-agent.js`: evidence collection and communication events.
- `session-store.js`: optional report session storage.
- `report-bridge.js`: selected-trip prefill and explicit save action in `../ryde-report/index.html`.

The project workflow, shared Python contracts and production application are not modified by this prototype. This is not a completed Rider Advocate or Judge implementation.
