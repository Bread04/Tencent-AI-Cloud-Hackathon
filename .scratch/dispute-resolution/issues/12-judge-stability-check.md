# 12: Judge stability check

**What to build:** A guard against the Judge being swayed by the order it reads the Submissions in. The Judge rules a second time with the Submission order swapped. If the outcome differs, or Confidence differs by more than a set margin, the Case is escalated as a Review Trigger and Confidence is capped. Submissions are presented to the Judge under neutral labels in a randomised order.

**Blocked by:** 09

**Status:** ready-for-agent

**Tier:** 1 · **Owner:** Braedon

- [x] Submissions are shown to the Judge under neutral labels in a randomised order (neutral labels `Submission A` and `Submission B`; the order of the first pass is set by a hash of the Case ID, so it varies between Cases and never for one Case; the Submission JSON still names its author)
- [x] Each Case is ruled twice with the order swapped (`judge_second_pass`; the second pass skips the self-check to save a call)
- [x] A differing outcome escalates the Case with "stability disagreement" as the trigger (`stability_disagreement`, shown in the review package and the Ruling tab)
- [x] A Confidence gap above the margin also escalates (a gap above `confidence.stability_margin`, 0.1; a gap exactly at the margin agrees)
- [x] Agreement between the two passes is recorded in the Communication Log (a `stability_check` row in the log, and a `stability` Confidence component: 0.95 on agreement, 0.5 on disagreement)
- [x] The margin is configurable and the check can be switched off (`switches.stability_check`, off by default; the console has a Stability check box)

**Fails closed:** if the second pass cannot be completed (the model fails or its draft stays invalid), the Case is held with that reason rather than passed unchecked.
**Demo:** tick Stability check in the console and run DISP-003. The scripted second pass turns the verdict round, so the Case is held; DISP-002 and DISP-004 agree.
**Limit:** the check doubles the Judge's calls. On a free model with a tokens-per-minute limit it makes a run noticeably slower.
