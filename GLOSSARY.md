# Ryde Dispute Resolution

Autonomous resolution of rider-driver disputes on a ride-hailing platform: agents gather evidence, argue each side, apply company policy, and issue a fair, explained ruling.

This is our entry in the Tencent Cloud AI Agent Hackathon (Singapore, 2026), Digital Native Track. The challenge is set by Ryde, a Singapore ride-hailing platform whose support teams resolve thousands of disputes a day by hand, slowly and inconsistently. We are building the working prototype, an architecture diagram, and a live demo, with a deadline of 15 October 2026.

## Language

### Hackathon

**Ryde**:
The Singapore ride-hailing and carpooling company that set the challenge and whose dispute process we are automating.
_Avoid_: The client, the platform (when meaning the company)

**Digital Native Track**:
The hackathon track whose single case study is Ryde's multi-agent dispute resolution challenge.
_Avoid_: The competition

**Core Agent**:
One of the three required agents (Rider Advocate, Driver Advocate, Judge) that the MVP must deliver, working on text and structured evidence.
_Avoid_: Main agent

**MVP**:
The required deliverable: the three Core Agents resolving at least two Dispute Categories end to end, with a visible Communication Log. Ours are Route Deviation and No-Show Charge.
_Avoid_: Prototype, v1

**Stretch Goal**:
An optional enhancement attempted only after the MVP works, earning bonus points: for example Escalation, Policy & Precedent, Image Analysis, or Property Damage.
_Avoid_: Extra, nice-to-have

**Communication Log**:
The visible record of how agents exchange information during a Case, shown so judges can see evidence requests, Submissions, and the Ruling. It shows decisions and citations, not private model reasoning.
_Avoid_: Trace, transcript

**Mock Data**:
Simulated trips, evidence, policies, and payment actions standing in for Ryde's real systems, always labelled as simulated when shown.
_Avoid_: Fake data, dummy data

**Demo Day**:
The live walkthrough where we show a dispute processed and resolved autonomously, after identifying the Ryde case study.
_Avoid_: Presentation, pitch

### Parties and roles

**Rider**:
The passenger on a trip.
_Avoid_: Customer, passenger, user

**Driver**:
The person operating the vehicle on a trip.
_Avoid_: Partner, captain

**Claimant**:
The party who filed the dispute, whether rider or driver.
_Avoid_: Complainant, plaintiff

**Respondent**:
The party the dispute is filed against.
_Avoid_: Defendant

### Dispute and case

**Dispute**:
A conflict between rider and driver over a trip, as filed by one party.
_Avoid_: Ticket, complaint

**Dispute Category**:
The kind of conflict a dispute concerns: route deviation, no-show charge, property damage, or safety incident.
_Avoid_: Dispute type

**Case**:
The system record built around one dispute: its evidence, both submissions, policy references, ruling, and communication log.
_Avoid_: Ticket

**Trip**:
A single ride from pickup to drop-off, or a cancelled attempt at one, that a dispute is tied to.
_Avoid_: Ride, booking

### Agents

**Rider Advocate**:
The agent that gathers evidence for, and argues the case of, the rider.
_Avoid_: Claimant agent

**Driver Advocate**:
The agent that gathers evidence for, and argues the case of, the driver.
_Avoid_: Respondent agent

**Judge**:
The impartial agent that weighs both submissions against policy and issues the ruling.
_Avoid_: Arbitrator, adjudicator

### Evidence and policy

**Evidence Item**:
A single record relevant to a case (a GPS trace, a chat message, a fare line, a photo) carrying its source and an ID that submissions can cite. Missing evidence is recorded as missing, never assumed.
_Avoid_: Proof, data point

**Submission**:
An advocate's structured argument for one party, citing Evidence Items and policy clauses.
_Avoid_: Case (reserved for the whole record), brief

**Policy Clause**:
A single rule of company policy that a submission or ruling can cite.
_Avoid_: Rule, guideline

### Outcome

**Ruling**:
The Judge's decision on a case: uphold, partially uphold, or reject the claimant's claim, with recommended action, amount where applicable, cited evidence and clauses, reasoning, and confidence.
_Avoid_: Decision, verdict, judgment

**Confidence**:
The Judge's measure of how well evidence completeness, consistency, and policy fit support the ruling.
_Avoid_: Certainty, probability

**Outcome**:
What each party is told after a ruling: the same ruling, worded for that party.
_Avoid_: Notification, result

**Escalation**:
Referral of a case to a human reviewer instead of finalizing the ruling, because confidence was too low or a review trigger applied.
_Avoid_: Handoff
