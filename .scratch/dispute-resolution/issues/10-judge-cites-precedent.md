# 10: Judge cites Precedent

**What to build:** The Policy & Precedent Agent. Alongside the applicable Policy Clauses, it returns a few similar past Rulings for a Case, with why each is similar, so the Judge can rule consistently. The store is seeded with mock past Rulings. The same policy version and the same Precedents are served to both advocates and the Judge. Precedent is advisory: the Judge may cite it, but evidence and policy take priority, and the Ruling says so when it departs from a Precedent. It is behind a switch.

**Port from the prototypes:** Kyven's `RiderPolicyAgent` (`prototypes/ryde-app/rider-policy-agent.js`, `rider-policy-agent.md` and `driver-policy-agent.md`) is ported to Python as roles of this one agent. Every role serves the same clause set and version (decided: no role-scoped filtering). Retrieval returns every materially relevant clause, not a list capped at five, with each clause's reason and the conditions still needing evidence.

**Blocked by:** 05

**Status:** ready-for-agent

**Tier:** 1 · **Owner:** Braedon

- [ ] A store of Precedents exists, seeded with mock past Rulings for both MVP categories
- [ ] Each Dispute Category has fixed Applicable Clauses, always served in full and identically to both advocates and the Judge; clauses are never retrieved by similarity
- [ ] For a Case, the agent returns the Applicable Clauses plus similar Precedents with the reason for similarity
- [ ] Precedents are ranked by category filter then tag overlap; with `precedent_retrieval = embeddings` they are reranked by a local open-source embedding model, and if that model is unavailable retrieval falls back to tags and says so in the Communication Log
- [ ] Only seeded and human-confirmed or overridden Rulings are retrievable; an unreviewed model Ruling is not, and each served Precedent carries its source
- [ ] A test fails if any Precedent contains a party identifier, trip ID or History-derived text
- [ ] A Ruling whose Remedy differs from a Precedent it was shown, with no explanation, fails the self-check once and then goes to review
- [ ] The tag and embedding modes are compared on the mock cases in the evaluation harness (ticket 20)
- [x] Both advocates and the Judge receive the same policy version
- [ ] A Ruling can cite Precedent IDs, and a citation to a missing Precedent is rejected
- [ ] When no Precedent is found, the Judge is told so explicitly
- [ ] A Ruling that departs from a cited Precedent explains why
- [ ] The Communication Log records the precedent retrieval
- [ ] With the switch off, the Judge rules from policy alone as before
