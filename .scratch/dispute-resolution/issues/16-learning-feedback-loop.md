# 16: Learning Feedback Loop

**What to build:** The system improves from corrections. When a Human Reviewer records an Override, it is captured with its reason and added to the precedent store as a new Precedent marked as coming from a human. A later similar Case retrieves that Precedent, and the Judge can cite it. Policy text is never silently changed: an Override becomes Precedent only. It is behind a switch.

**Blocked by:** 09, 10

**Status:** ready-for-agent

**Tier:** 4 · **Owner:** Braedon

- [x] An Override creates a Precedent with source marked as human override, including the reason
- [x] A later similar Case retrieves that Precedent
- [x] A demo pair of mock cases shows it: the first is overridden, the second cites the Override
- [x] Policy Clauses are unchanged by an Override
- [x] The Communication Log records the new Precedent
- [x] With the switch off, Overrides are recorded but not added to the store

**How it works:** `src/agents/learning.py` turns an Override into a `human_override` Precedent (tags and the reviewer's reason only: no evidence, party, trip, reviewer name or History). `decide_review` calls it when `switches.learning_loop` is on; the Precedent lives in the Case store (`human_precedents()`), is retrieved with the seeded ones, and the Judge is shown the reviewer's reason. Console box: Learn from overrides (live runs only; it is not in the recorded streams).
**Demo pair:** with Use precedent and Learn from overrides ticked, run DISP-004 (held on low Confidence), override it at `/review` with a reason, then run DISP-007: it retrieves the Override and the Judge cites it, explaining why this Case differs (`fixtures/stub/DISP-007.learning.json`).
**Limits:** only categories with a tag vocabulary (No-Show, Safety Incident) learn; for Route Deviation and Property Damage the log says no Precedent was added. Precedents are in memory, so they reset with the server. The reviewer's free-text reason goes in as written, so a reason that names a party or trip would leak it.
