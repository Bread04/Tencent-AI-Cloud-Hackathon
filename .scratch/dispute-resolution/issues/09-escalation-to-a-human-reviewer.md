# 09: Escalation to a Human Reviewer

**What to build:** A Ruling that should not be finalized automatically goes to a person. When Confidence is below the threshold, or a Review Trigger applies, the Ruling stays proposed, both parties are told that review is pending, and the Case joins a human review queue with a review package: both Submissions, the evidence, the policy cited, the proposed Ruling, and the reason for review. A Human Reviewer opens the Case on a reviewer screen and confirms the Ruling or records an Override with a reason. The parties then get the final Outcome. Escalation is behind a switch.

**Blocked by:** 05, 07

**Status:** ready-for-agent

**Tier:** 1 · **Owner:** Braedon

- [ ] A Ruling below the Confidence threshold is not finalized and the Case becomes pending review
- [ ] A failed stage (exhausted repair budget, unreachable model) also sends the Case to review with its reason
- [x] Both parties see a "review pending" Outcome
- [ ] The review package contains both Submissions, evidence, policy cited, the proposed Ruling and the trigger
- [ ] A reviewer screen lists pending Cases and shows the package
- [ ] The reviewer can confirm, or override with a required reason
- [ ] After review, both parties receive the final Outcome
- [x] The threshold is configurable
- [ ] With Escalation switched off, every Ruling finalizes as before
- [ ] A mock case exists that escalates on low Confidence
