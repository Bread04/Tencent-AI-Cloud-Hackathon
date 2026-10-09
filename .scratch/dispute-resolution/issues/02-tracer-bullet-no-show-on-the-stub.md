# 02: Tracer bullet: one No-Show Dispute resolved end to end on the stub

**What to build:** The thinnest possible path through the whole system. A user picks one prepared No-Show Charge Dispute and runs it. The system validates it, gathers the evidence for that Trip, has the Rider Advocate and Driver Advocate each file a Submission, has the Judge issue a Ruling, and shows the Ruling and the Communication Log on a bare page. Model replies are scripted by the stub, so nothing depends on a real provider. The mock case is a cleaned copy of the DISP-002 sample: the inconsistent speeds are fixed, and the expected ruling and evidence summary are moved to a separate evaluation label the agents never read.

**Blocked by:** 01

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Kyven and Braedon together

- [ ] Running the prepared Dispute produces a Case that reaches a ruled state
- [ ] The Case holds Evidence Items for GPS, chat, fare and History, each with an ID and a status
- [ ] Both advocates file a Submission, and neither sees the other one
- [ ] The Judge returns a Ruling with outcome, amount, Confidence and reasoning
- [ ] The Communication Log shows evidence requests and responses, both Submissions and the Ruling, in order
- [ ] A bare page shows the Ruling and the log for the run
- [ ] An invalid Trip reference or Dispute Category is rejected with a clear error
- [ ] The end-to-end test passes with no network access
- [ ] The agents never receive the expected-outcome label
