# 03: No-Show rulings cite mock policy

**What to build:** One shared policy source for No-Show Charge disputes: the Waypoint clauses in `prototypes/shared/policies.js`, ported to the backend with stable IDs and one version. The source is generic and sets no wait time or fee, so the thresholds come from the trip's fare evidence and code computes whether each was reached, counting from the driver's arrival (see ADR 0002). Advocates and the Judge look up the clauses for a Dispute Category and cite them by ID. A citation to a clause that does not exist is rejected in code. The policy is labelled as a draft, not Ryde's approved terms, wherever it is shown.

**Blocked by:** 02

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Braedon

- [x] No-Show policy is served as Policy Clauses (the shared Waypoint set), each with a stable ID, text and version
- [x] The free-wait and no-show threshold ambiguity is resolved in code from the fare evidence, counted from arrival (ADR 0002); the policy text states no numbers
- [x] The closed Remedy list and the no-partial-outcome rule for No-Show are enforced by the Judge: only uphold with fee_reversal or reject with no_action are allowed (the shared policy set does not state them)
- [x] A material-evidence checklist for No-Show is available through the policy module
- [x] Looking up policy for the No-Show category returns the applicable clauses
- [x] A Submission or Ruling citing a non-existent clause ID fails validation with a clear error
- [x] The Communication Log records a policy lookup event
- [x] The policy is labelled as a draft, not Ryde's approved terms, on screen
