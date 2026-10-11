# Wait and no-show thresholds come from trip data, not policy text

The shared policy set (`prototypes/shared/policies.js`, Kyven) is deliberately generic: its No-Show clause says "This draft sets no fixed waiting period or fee." The free-wait period and the no-show threshold therefore live in the trip's own data (`cancellation_policy` in the mock case, carried in the fare Evidence Item), and code computes from them whether each was reached. The clock starts at the driver's arrival at the pickup point, not at the scheduled pickup time. The policy text never states a number.

## Considered Options

- **Write the thresholds into mock policy clauses** (what ticket 03 first did, as clauses NS-1 to NS-7). Rejected: it invented a rule that the shared policy source says it does not have, and left two policy sources that could drift apart.
- **Add a No-Show addendum to the shared policy set.** Rejected for now: it would change Kyven's file and the numbers (5 and 8 minutes) come from the hackathon sample dataset, not from any policy.

## Consequences

- One policy source, ported by `scripts/sync_policy.cjs`; a test fails if the Python copy drifts from the JS file.
- Each mock case can carry its own thresholds, so the three No-Show cases can differ without touching policy.
- The closed Remedy list is the `Remedy` enum in the contract. A partial outcome on a No-Show case is allowed only where a Policy Clause provides for one, and none does, so No-Show is all or nothing. The Judge enforces it with the `ALLOWED_REMEDIES` table in `src/agents/policy`: only `uphold` with `fee_reversal` and `reject` with `no_action` are allowed.
- Route Deviation (ticket 06) needs a refund formula that the shared policy set also lacks. It will need the same treatment: a decision on where the formula lives.
