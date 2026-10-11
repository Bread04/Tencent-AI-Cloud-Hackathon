# 18: Extend the contract for report fields, version references and resealing

**What to build:** The contract changes the connected workflow needs, agreed with Kyven and made once. The Dispute keeps the filed report as it was submitted, together with its incident time, time zone and location, its category details, and its requested resolution (type, amount, currency), so the advocates and Evidence Agents can read them. A Submission records the report, evidence and policy versions it was built from. The Case store can seal a new evidence version after a policy gap exposes a missing record; sealing again invalidates the Submissions and Ruling built on the old version and logs it. The Policy Clause stays without a role.

**Blocked by:** 02

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Kyven and Braedon together

- [ ] The filed report's incident, category-detail and requested-resolution fields are held on the Dispute and rejected when malformed
- [ ] A Submission carries the report, evidence and policy versions it was built from, and a Submission built on a stale version is refused
- [ ] Sealing a second evidence version is allowed once, logs an event, and marks earlier Submissions and the Ruling as stale
- [ ] Existing contract objects and tests still pass, and the shared contract file is changed only in this ticket
- [ ] The decisions are recorded in docs/contract-decisions.md
