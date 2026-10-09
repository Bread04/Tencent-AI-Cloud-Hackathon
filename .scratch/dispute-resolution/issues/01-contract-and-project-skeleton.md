# 01: Contract and project skeleton

**What to build:** The shared foundation both teammates build on. The contract objects from the architecture doc exist as validated types (Dispute, Case, Evidence Item, Submission, Policy Clause, Precedent, Ruling, Outcome, Log event). A configuration lists each Supporting Agent as switched on or off. A model adapter exists with an offline stub that returns scripted replies. A Case store can create a Case, accept writes, and emit a Log event for every write. The open decisions from the contract session (Confidence components and caps, escalation threshold, escalation triggers, structured-output format) are recorded where the code reads them.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Kyven and Braedon together

- [ ] The project installs and its test suite runs with one command
- [ ] Every contract object validates good input and rejects bad input with a clear error
- [ ] A test creates a Case in the store, writes to it, reads it back, and sees one Log event per write
- [ ] The model stub returns a scripted reply for a given case without any network access
- [ ] All Supporting Agent switches exist and default to off
- [ ] The contract session decisions are written down in the repo
