# 07: Demo UI

**What to build:** The web interface a presenter uses on Demo Day. They pick a prepared mock Dispute, run it with one click, and watch the Communication Log fill in live as agents request evidence, file Submissions and rule. When the Case is ruled they see a Ruling card and the rider and driver Outcome views side by side. They can open any Case and see its Evidence Items, both Submissions, the Ruling and the log together. Everything simulated is labelled as simulated.

**Blocked by:** 02

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Braedon

- [x] A list of prepared mock Disputes can be browsed and one run with a single click
- [ ] The Communication Log updates live during a run
- [ ] The Ruling card shows outcome, amount, Confidence with its components, reasoning, per-argument assessment, and cited evidence and clauses
- [ ] Cited Evidence Items and Policy Clauses can be opened from the Ruling
- [ ] Rider and driver Outcome views are shown side by side
- [ ] A recommended action is visibly different from an executed one
- [x] Mock data, mock policy and simulated financial actions are labelled on screen
- [ ] The UI can be built against a recorded log stream, without the orchestrator running
