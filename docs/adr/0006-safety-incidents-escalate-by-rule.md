# Safety Incidents escalate by rule, not by a higher confidence threshold

A Safety Incident always goes to a Safety Officer, whatever the Judge's confidence. We did not raise the global
confidence threshold to catch them.

**Why not the threshold.** It is one number for every category, so raising it enough to catch safety cases would send
most ordinary No-Show and Route Deviation Cases to a person too. Confidence also measures how sure the Judge is, not
how serious the Case is: a confidently wrong Judge would still finalize a safety Case above the line. A rule on the
category cannot be argued out of escalating.

**What follows.**

- A Safety Incident is a Review Trigger, and it is held even at Confidence 0.95.
- It is never rejected as unsupported, including when SLA routing is off. It goes to the review queue with no Priority
  and a note saying why.
- It reaches the queue as soon as it is filed, marked as awaiting a proposal, and the Judge's draft is attached when it
  finishes. A person does not wait on model latency.
- The Judge still drafts a proposal, but it is labelled as a fare remedy only. The system does not rule on whether the
  driver's conduct was dangerous; the Safety Officer investigates that outside it.
- While the Case is pending, the rider is told a Safety Officer is reviewing it as a priority. The driver is told only
  that a report is under review, with no detail of the allegation.

Ryde publishes no severity tiers and no response time for safety reports, so "always to a person, at once" is our own
mock rule, consistent with what Ryde publishes and stricter than it.
