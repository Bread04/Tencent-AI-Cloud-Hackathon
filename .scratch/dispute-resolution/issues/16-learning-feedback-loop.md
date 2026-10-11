# 16: Learning Feedback Loop

**What to build:** The system improves from corrections. When a Human Reviewer records an Override, it is captured with its reason and added to the precedent store as a new Precedent marked as coming from a human. A later similar Case retrieves that Precedent, and the Judge can cite it. Policy text is never silently changed: an Override becomes Precedent only. It is behind a switch.

**Blocked by:** 09, 10

**Status:** ready-for-agent

**Tier:** 4 · **Owner:** Braedon

- [ ] An Override creates a Precedent with source marked as human override, including the reason
- [ ] A later similar Case retrieves that Precedent
- [ ] A demo pair of mock cases shows it: the first is overridden, the second cites the Override
- [ ] Policy Clauses are unchanged by an Override
- [ ] The Communication Log records the new Precedent
- [ ] With the switch off, Overrides are recorded but not added to the store
