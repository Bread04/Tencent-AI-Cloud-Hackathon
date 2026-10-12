# 10: Judge cites Precedent

**What to build:** The Policy & Precedent Agent. Alongside the applicable Policy Clauses, it returns a few similar past Rulings for a Case, with why each is similar, so the Judge can rule consistently. The store is seeded with mock past Rulings. The same policy version and the same Precedents are served to both advocates and the Judge. Precedent is advisory: the Judge may cite it, but evidence and policy take priority, and the Ruling says so when it departs from a Precedent. It is behind a switch.

**Port from the prototypes:** Kyven's `RiderPolicyAgent` (`prototypes/ryde-app/rider-policy-agent.js`, `rider-policy-agent.md` and `driver-policy-agent.md`) is ported to Python as roles of this one agent. Every role serves the same clause set and version (decided: no role-scoped filtering). Retrieval returns every materially relevant clause, not a list capped at five, with each clause's reason and the conditions still needing evidence.

**Blocked by:** 05

**Status:** ready-for-agent

**Tier:** 1 · **Owner:** Braedon

- [x] A store of Precedents exists, seeded with mock past Rulings for both MVP categories (`data/precedents/seed.json`: six No-Show, four Safety Incident and two Route Deviation, `src/agents/policy/precedents.py`)
- [x] Each Dispute Category has fixed Applicable Clauses, always served in full and identically to both advocates and the Judge; clauses are never retrieved by similarity (done for No-Show; Route Deviation has no clause list until ticket 06)
- [x] For a Case, the agent returns the Applicable Clauses plus similar Precedents with the reason for similarity
- [x] Precedents are ranked by category filter then tag overlap; with `precedent_retrieval = embeddings` they are reranked by a local open-source embedding model, and if that model is unavailable retrieval falls back to tags and says so in the Communication Log (the embedding rerank and the fallback are built behind an `Embedder` interface and tested with a fake model; `fastembed` is not installed, so with `retrieval = embeddings` today it falls back to tags and says so in the log)
- [x] Only seeded and human-confirmed or overridden Rulings are retrievable; an unreviewed model Ruling is not, and each served Precedent carries its source (`PrecedentSource` gained `seeded` and `human_confirmed`)
- [x] A test fails if any Precedent contains a party identifier, trip ID or History-derived text
- [x] A Ruling whose Remedy differs from a Precedent it was shown, with no explanation, fails the self-check once and then goes to review (enforced as a code rule in the Judge's draft check: it is sent back with the problem up to the repair budget, then the Case goes to review)
- [ ] The tag and embedding modes are compared on the mock cases in the evaluation harness (ticket 20)
- [x] Both advocates and the Judge receive the same policy version
- [x] A Ruling can cite Precedent IDs, and a citation to a missing Precedent is rejected
- [x] When no Precedent is found, the Judge is told so explicitly
- [x] A Ruling that departs from a cited Precedent explains why (stated in `precedent_departure` and appended to the reasoning)
- [x] The Communication Log records the precedent retrieval
- [x] With the switch off, the Judge rules from policy alone as before (`switches.policy_precedent`, off by default; the console has a Use precedent box)

**Still open:** the tag-versus-embedding comparison needs the evaluation harness (ticket 20), and a real embedding model (`fastembed`, ADR 0003) has not been installed or tried. The Learning Feedback Loop (ticket 16) is what will add human-confirmed Precedents.
**Safety Incidents:** four seeded precedents (PREC-SF-01 to 04) are served to Safety Incident cases, with tags drawn from the trip record (speed, app alerts, the rider's complaints, how the trip ended). They are served only when the precedent and SLA routing switches are both on.
