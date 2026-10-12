# 05: Real Judge for No-Show

**What to build:** The Judge weighs both Submissions against the underlying evidence and policy and issues a Ruling for No-Show Charge disputes. The full design is in section 5.6 of the architecture doc.

In one structured model call it gives each argument an Argument Assessment (accepted, rejected, unproven, or not decisive, with a reason), states the Balance of Evidence, chooses the outcome and a Remedy from the closed list in policy, and gives Policy Fit as clear, arguable or unclear. A second model call checks that each cited item supports the claim made about it; code checks everything else. The Judge does no arithmetic and produces no Confidence number: code computes the amount from the fare evidence and Confidence as the lowest of its components. The Claimant bears the Burden of Proof. History is withheld from the Judge and applied afterwards by a rule table in code. A template then writes each party's Outcome from the finished Ruling. The Judge can be called on fixture Submissions without the advocates running.

**Blocked by:** 02, 03

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Braedon

- [x] The Judge can be run directly on a Case plus two fixture Submissions
- [x] Every argument in both Submissions gets one of the four Argument Assessments with a reason and the evidence it turned on
- [x] The Ruling states the Balance of Evidence; a balanced Case is marked for review and its Ruling is a proposal
- [x] An unproven claim by the Claimant is rejected
- [x] The Remedy is one the category allows (`ALLOWED_REMEDIES`); a partial outcome on a No-Show case is not available because no Policy Clause provides for one
- [x] The amount is computed by code from the inputs the Judge names, and the Ruling shows the calculation
- [x] Confidence is computed by code as the lowest component; the Judge supplies only the Policy Fit level
- [x] The material-evidence checklist for No-Show is shown in the Ruling with what was missing
- [x] The prompt given to the Judge contains no History
- [x] The History step can lower Confidence or add a Review Trigger, lists each adjustment with a reason, and never changes the outcome
- [x] A point neither advocate raised is labelled as an Own Finding, and a decisive one caps Confidence
- [x] A situation no clause covers is named as a Policy Gap, Policy Fit is unclear, and the Case is marked for review
- [x] Every cited Evidence Item and Policy Clause ID exists
- [x] A failed self-check sends the draft back once, then the Case goes to review
- [x] The Ruling is stored with the Case, and reopening the Case does not rerun the Judge
- [x] On the three No-Show mock cases the Judge's rules produce the expected label on scripted replies (`tests/test_mock_cases.py`): DISP-002 reject, DISP-003 uphold with a 5.00 fee reversal, and DISP-004 a proposal held for review at Confidence 0.5, below the escalation threshold
- [ ] The same three labels are matched with a real model, not scripted replies (moved to ticket 20, needs 04 and 08)
- [x] Each party's Outcome is produced by a template from the Ruling, with the action marked recommended, not executed
