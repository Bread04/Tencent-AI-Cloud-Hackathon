# 13: SLA & Routing with Safety Incident

**What to build:** The SLA & Routing Manager and the Safety Incident category together, because priority is only visible with a case that needs it. When a Dispute is filed it gets a Priority from its category, urgency and value, with a reason. Safety Incidents get the highest Priority and are always escalated, whatever the Confidence. The human review queue is ordered by Priority, so a Safety Incident filed after several ordinary cases appears at the front. Mock Safety Incident cases exist. When no category is chosen, intake can classify the description into one. It is behind a switch.

**Blocked by:** 09

**Status:** ready-for-agent

**Tier:** 2 · **Owner:** Braedon (SLA and queue) and Kyven (mock cases and intake)

- [x] Every Case gets a Priority and a reason when filed (`src/agents/routing.py`: category points, +30 for safety-related words, +1 per SGD 10 of the amount; the numbers are placeholders)
- [x] The review queue is ordered by Priority (`/api/review` sorts by priority, then oldest first)
- [x] At least two Safety Incident mock cases exist with expected-outcome labels (DISP-005 strong evidence and DISP-006 weak evidence, with `.eval.json` labels and scripted replies)
- [x] A Safety Incident always escalates, even with high Confidence (`apply_escalation(safety_incident=True)`; held even with the escalation switch off)
- [x] A Safety Incident filed last appears first in the queue (tested through the API)
- [x] A Dispute with no category chosen is classified into one, or rejected with a clear error (`src/agents/intake.py` and `POST /api/classify`; not wired into a filing flow until ticket 19)
- [x] The Priority and its reason show in the UI and the Communication Log (the case header, the review queue and a `priority_set` log row)
- [x] With the switch off, all Cases share one Priority and earlier cases still resolve (`switches.sla_routing`, off by default: every Case has priority 0 and a Safety Incident is turned away as unsupported, as before)

**Demo:** tick SLA routing in the console and run DISP-005 or DISP-006: both are held with the `safety_incident` trigger even at Confidence 0.95. Run an ordinary held case first (DISP-004 with routing on), then DISP-005, and open Review queue: the Safety Incident is first.
**Limits:** a Safety Incident Ruling is only a proposal: a reviewer confirming it recommends a full refund, and conduct review happens outside this system. The classifier is keyword rules, not a model.
