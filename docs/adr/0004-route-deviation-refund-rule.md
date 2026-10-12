# Route Deviation uses a recomputed optimal net fare

Approved for the simulated Ticket 06 cases. Policy clauses R-04, D-04, R-03 and
D-03 remain unchanged. A longer route is evidence for review, never proof of
fault, consent, or refund entitlement. The Judge weighs both Submissions first.

The receipt's paid net fare is authoritative. A complete, nonnegative tariff,
positive surge, explicit promotion (including zero), SGD receipt, supplied
simulated road baseline, expected duration and travelled route are required.
The tariff applied to the actual route and duration must reconcile to the
receipt at SGD cents. Missing or invalid inputs mean an unavailable calculation
and human review; no defaults are supplied.

`optimal_net = max(0, (base + optimal_km * km_rate + expected_minutes * minute_rate) * surge + booking + tolls - promo)`

`refund = min(paid_net, max(0, paid_net - optimal_net))`

Money uses Decimal; only final SGD cents are rounded half-up. Haversine route
segments use Earth radius 6,371,000m; distances are rounded half-up to 0.001km
and elapsed durations to 0.01 minute before tariff arithmetic. The baseline is
supplied simulated road geometry, not a live shortest-path or traffic claim.
Receipt tolls, booking and promotion are held constant for this comparison;
no hypothetical toll or promotion eligibility is invented.

Stop candidates cluster samples within 25m of the first sample for at least
120 seconds. Candidates within 50m of either endpoint are excluded. Sampling
gaps over 120 seconds (or explicit gap markers) are never bridged; their path
and dwell are unknown. Two endpoints alone are insufficient route evidence.
Candidates establish observed stationary intervals only, never stop purpose.

Calculations cite the route and fare Evidence Item IDs and this ADR, and show
formula and input values in the existing Calculation.formula field. Consent
must cite the exact Rider message and message ID, and covers only the described
detour. Unclear consent/explanation yields a balanced proposal pending review,
with no authorised amount. A partial refund is less than the full fare requested.
No payments are executed. History remains withheld until after the outcome.

Route availability also requires matching booked endpoints and full coverage between the supplied Trip start/completion times. Named simulated landmarks are matched to route samples within 50m; these bounded observations let agents assess the scope of a named detour without receiving raw geometry. A receipt must have an ID, match the Trip ID and completion timestamp. Missing conversation is missing evidence, not proof of no consent. Route proposals with later History review triggers also withhold monetary fields.

## Python execution amendment (2026-10-12)

The Rider Evidence, Policy and Advocate agents and ordered case preparation run
in `src/agents/rider/`. Both web pages require FastAPI. The trusted public Rider
catalog is `data/prototype/rider-catalog.json`, extracted once from RydeDemo and
kept synchronized for route samples by `scripts/build_route_samples.py`. Python
uses the existing shared policy JSON, including its richer clause metadata.
`src/tools/evidence/route.py` is the sole route/fare calculator; the duplicate
browser calculator and executable JavaScript agents were removed. This changes
execution placement only, not the approved fare rule or shared contracts.

The bounded Rider API accepts report text/media metadata and simulated scope,
never client telemetry or policy. It creates and stores its actual public log in
`RiderTranscripts`, returning redacted activity arrays and an opaque owner-cookie
handle. Standalone evidence uses the same locked log. Legacy client registration
remains solely for saved-log migration. Offline preparation preserves the report
and shows a retry error without local rules fallback.
