# 09: Escalation to a Human Reviewer

**What to build:** A Ruling that should not be finalized automatically goes to a person. When Confidence is below the threshold, or a Review Trigger applies, the Ruling stays proposed, both parties are told that review is pending, and the Case joins a human review queue with a review package: both Submissions, the evidence, the policy cited, the proposed Ruling, and the reason for review. A Human Reviewer opens the Case on a reviewer screen and confirms the Ruling or records an Override with a reason. The parties then get the final Outcome. Escalation is behind a switch.

**Blocked by:** 05, 07

**Status:** ready-for-agent

**Tier:** 1 · **Owner:** Braedon

- [x] A Ruling below the Confidence threshold is not finalized and the Case becomes pending review
- [x] A failed stage (exhausted repair budget, unreachable model) also sends the Case to review with its reason
- [x] Both parties see a "review pending" Outcome
- [x] The review package contains both Submissions, evidence, policy cited, the proposed Ruling and the trigger
- [x] A reviewer screen lists pending Cases and shows the package
- [x] The reviewer can confirm, or override with a required reason
- [x] After review, both parties receive the final Outcome
- [x] The threshold is configurable
- [x] With Escalation switched off, every Ruling finalizes as before
- [x] A mock case exists that escalates on low Confidence

**How it works:** `src/agents/escalation.py` (the decision, the review package and the reviewer's decision), `src/api/review.py` and `src/api/review.html` (the queue and screen at `/review`). Run `uv run uvicorn src.api.demo:app`, run DISP-004 from the console, then open Review queue.
**Limit:** a Case held because a stage failed (no Ruling) is listed in the queue with its reason but cannot be confirmed or overridden, because there is nothing to confirm. It needs a re-run.
**Decision:** the History step is now 0.05 per rule so DISP-002 resolves; see `docs/contract-decisions.md`.
**Triggers now held in code:** low Confidence (after History), balanced evidence, a Policy Gap, a History rule, a failed stage, and a Ruling amount above `CONFIG.escalation.amount_limit`. With Escalation off every Ruling finalizes; a Case whose stage failed has no Ruling to finalize, so it is still held.
**Not done:** the other triggers in architecture 5.7 that need Tier 2 to 3 features (Safety Incident, photo authenticity, stability check). The review package lists every policy clause that applied to the Case, with the ones the Ruling cites named in the proposed Ruling. The store has no lock, so two reviewers deciding at the same instant could both pass the check; fine for a single-presenter demo.
