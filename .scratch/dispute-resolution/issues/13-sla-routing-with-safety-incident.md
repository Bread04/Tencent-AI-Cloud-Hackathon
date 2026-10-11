# 13: SLA & Routing with Safety Incident

**What to build:** The SLA & Routing Manager and the Safety Incident category together, because priority is only visible with a case that needs it. When a Dispute is filed it gets a Priority from its category, urgency and value, with a reason. Safety Incidents get the highest Priority and are always escalated, whatever the Confidence. The human review queue is ordered by Priority, so a Safety Incident filed after several ordinary cases appears at the front. Mock Safety Incident cases exist. When no category is chosen, intake can classify the description into one. It is behind a switch.

**Blocked by:** 09

**Status:** ready-for-agent

**Tier:** 2 · **Owner:** Braedon (SLA and queue) and Kyven (mock cases and intake)

- [ ] Every Case gets a Priority and a reason when filed
- [ ] The review queue is ordered by Priority
- [ ] At least two Safety Incident mock cases exist with expected-outcome labels
- [ ] A Safety Incident always escalates, even with high Confidence
- [ ] A Safety Incident filed last appears first in the queue
- [ ] A Dispute with no category chosen is classified into one, or rejected with a clear error
- [ ] The Priority and its reason show in the UI and the Communication Log
- [ ] With the switch off, all Cases share one Priority and earlier cases still resolve
