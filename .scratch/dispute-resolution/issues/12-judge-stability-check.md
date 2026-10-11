# 12: Judge stability check

**What to build:** A guard against the Judge being swayed by the order it reads the Submissions in. The Judge rules a second time with the Submission order swapped. If the outcome differs, or Confidence differs by more than a set margin, the Case is escalated as a Review Trigger and Confidence is capped. Submissions are presented to the Judge under neutral labels in a randomised order.

**Blocked by:** 09

**Status:** ready-for-agent

**Tier:** 1 · **Owner:** Braedon

- [ ] Submissions are shown to the Judge under neutral labels in a randomised order
- [ ] Each Case is ruled twice with the order swapped
- [ ] A differing outcome escalates the Case with "stability disagreement" as the trigger
- [ ] A Confidence gap above the margin also escalates
- [ ] Agreement between the two passes is recorded in the Communication Log
- [ ] The margin is configurable and the check can be switched off
