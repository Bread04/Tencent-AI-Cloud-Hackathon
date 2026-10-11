# 03: No-Show rulings cite mock policy

**What to build:** A mock company policy for No-Show Charge disputes, written as Policy Clauses with stable IDs and one version. It resolves the ambiguity in the sample data explicitly: whether the free wait counts from the arrival of the driver or from the scheduled pickup time, and whether the fee applies at the free-wait limit or at the no-show threshold. Advocates and the Judge look up the clauses for a Dispute Category and cite them by ID. A citation to a clause that does not exist is rejected in code. The policy is labelled as simulated wherever it is shown.

**Blocked by:** 02

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Braedon

- [x] No-Show policy exists as Policy Clauses, each with a stable ID, text and version
- [x] The free-wait and no-show threshold ambiguity is resolved in the wording
- [x] The policy defines the closed list of Remedies and says whether No-Show allows a partial outcome
- [x] A material-evidence checklist for No-Show is kept with the policy
- [x] Looking up policy for the No-Show category returns the applicable clauses
- [x] A Submission or Ruling citing a non-existent clause ID fails validation with a clear error
- [x] The Communication Log records a policy lookup event
- [x] The policy is labelled as simulated on screen
