# Public Rider catalog

`rider-catalog.json` is the trusted Python runtime source for all eleven current
Rider app trips and six simulated Rider identities. Nine reports (DISP-002–010)
cover No-show / cancellation, Safety / conduct and Route deviation. It is synchronized from
the public `RydeDemo` API in `prototypes/ryde-app/data.js` with Node, including only
its public Rider records. Histories, evaluation labels and private Driver
statements are excluded. Browser-supplied telemetry and policy are rejected.

The browser retains `data.js` for rendering and synchronous selection only.
`scripts/build_route_samples.py` updates both route projections from the same
authoring data. `scripts/build_remaining_samples.py` reproducibly curates public
DISP-005–007 data from the unchanged source fixtures, before the route builder's
owned block. Safety receipts are absent (`null`), so fare is unavailable, not zero.
Safety reports preserve their original remedies and stay on the existing
`support_required` path; no reviewer is dispatched. DISP-007's attributed chat,
including instruction-like text and the call type, remains untrusted data.
`route-analysis.test.cjs` checks full catalog/UI parity;
`tests/test_rider_agents.py` and `tests/test_rider_api.py` check Python arithmetic,
policy metadata, ownership and source/API parity. No second calculator or policy
store is used. Policy titles, categories and keywords already exist in
`data/policy/waypoint-singapore-draft-2026-10.json` (synchronized by
`scripts/sync_policy.cjs`).

Rider selection is simulated identity, not production authentication. The
FastAPI server is mandatory for all Rider agents, policy preview and locked logs.
