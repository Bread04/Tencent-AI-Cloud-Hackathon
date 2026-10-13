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
The challenge brief's term for an optional enhancement that earns bonus points once the MVP works. We are attempting all of them except Fraud and Bad-Faith Detection.
_Avoid_: Extra, nice-to-have

**Supporting Agent**:
Any agent beyond the three Core Agents: the Evidence Agents, Policy & Precedent Agent, Image Analysis, Escalation Protocol, SLA & Routing Manager, and Learning Feedback Loop. Each can be switched off without breaking the Core Agents.
_Avoid_: Subagent, optional agent, helper

**Tier**:
A layer of the build, delivered in order: Tier 0 is the MVP, and each later Tier adds Supporting Agents or Dispute Categories. A Tier must work end to end before the next one starts.
_Avoid_: Phase, milestone, sprint

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

**Filed Report**:
The report form a party submitted, kept on the Dispute exactly as it was sent. Its incident time and place, category details and Requested Resolution are also held as checked fields that agents read; the raw report itself is never sent to a model.
_Avoid_: Complaint form, ticket

**Requested Resolution**:
What the filing party asked for on the report form: a type and, where given, an amount and currency. It is the party's request only; what the Ruling grants is the Remedy.
_Avoid_: Remedy (reserved for what the Ruling grants), claim amount

### Agents

**Rider Advocate**:
The agent that argues the rider's case, citing evidence and policy. It stays the rider's advocate whether the rider is Claimant or Respondent.
_Avoid_: Claimant agent

**Driver Advocate**:
The agent that argues the driver's case, citing evidence and policy. It stays the driver's advocate whether the driver is Claimant or Respondent.
_Avoid_: Respondent agent

**Judge**:
The impartial agent that weighs both submissions against the evidence and policy and issues the ruling.
_Avoid_: Arbitrator, adjudicator

**Evidence Agent**:
A Supporting Agent that collects and organises the evidence relevant to one party's position. There are two, the Rider Evidence Agent and the Driver Evidence Agent, and both read the same records.
_Avoid_: Evidence Collection Agent, retriever

**Policy & Precedent Agent**:
The Supporting Agent that serves the applicable Policy Clauses and similar Precedents to both advocates and the Judge, from one shared source.
_Avoid_: Policy agent for rider's side, policy agent for driver's side, knowledge base

**Image Analysis**:
The Supporting Agent that turns a submitted photo into evidence: what it shows, plus its Authenticity Checks.
_Avoid_: Computer vision, photo agent

**SLA & Routing Manager**:
The Supporting Agent that assigns each Case its Priority and orders the human review queue by it.
_Avoid_: Queue manager, router

**Learning Feedback Loop**:
The capability that turns a Human Reviewer's Override into a new Precedent, so later similar Cases see the correction.
_Avoid_: Retraining, fine-tuning

### Evidence and policy

**Evidence Item**:
A single record relevant to a case (a GPS trace, a chat message, a fare line, a photo) carrying its source and an ID that submissions can cite. Missing evidence is recorded as missing, never assumed.
_Avoid_: Proof, data point

**Material Evidence**:
The evidence a Dispute Category cannot be fairly decided without, listed in a checklist kept with the policy. When some of it is missing, Confidence drops.
_Avoid_: Key evidence, required fields

**Evidence Version**:
The ID a Case's evidence set gets when it is sealed, after which nothing can be added. A Submission records the report, Evidence and policy versions it was built from, and one built on a version no longer in force is refused.
_Avoid_: Snapshot, revision

**Reseal**:
Adding a record the first Evidence Version lacked and sealing a second version, allowed once per Case and never after a final Ruling. The Submissions and Ruling built on the first version become Stale.
_Avoid_: Reopen, amend

**Stale**:
Said of a Submission or Ruling built on an Evidence Version that a Reseal replaced. It is kept on the Case for the record, apart from the current ones, and is never argued from or acted on.
_Avoid_: Outdated, invalid

**Submission**:
An advocate's structured argument for one party, citing Evidence Items and policy clauses.
_Avoid_: Case (reserved for the whole record), brief

**Policy Clause**:
A single rule of company policy that a submission or ruling can cite.
_Avoid_: Rule, guideline

**Applicable Clauses**:
The Policy Clauses a Dispute Category requires, always served in full and identically to both Advocates and the Judge. Anything else the Policy & Precedent Agent finds relevant is added on top, never in place of them.
_Avoid_: Mandatory clauses, retrieved clauses, matched clauses

**Precedent**:
A past Ruling on a similar Case, offered to the Judge for consistency. It is advisory: evidence and policy take priority over it, and a Ruling that differs from a Precedent it was shown must say why. Only seeded and human-confirmed or overridden Rulings qualify, and a Precedent never identifies the parties or draws on their History.
_Avoid_: Case law, history (reserved for a party's past behaviour)

**Authenticity Check**:
An assessment of whether a photo can be trusted as evidence: whether its timestamp aligns with the Trip, and whether it shows signs of AI generation. Its result is a signal with stated uncertainty, never proof.
_Avoid_: Verification, fraud check

**History**:
A party's past behaviour on the platform: prior disputes, ratings, and account age. It is withheld from the Judge until the outcome is decided, and afterwards may only adjust Confidence or trigger review, never change the outcome.
_Avoid_: Profile, record, reputation

### Outcome

**Ruling**:
The Judge's decision on a case: uphold, partially uphold, or reject the claimant's claim, with a Remedy, amount where applicable, cited evidence and clauses, reasoning, and confidence. Partially uphold means the Claimant gets less than they asked for.
_Avoid_: Decision, verdict, judgment

**Remedy**:
The action a Ruling recommends, chosen from a closed list defined in policy: full refund, partial refund, fee reversal, compensation to the driver, or no action. The Judge chooses the Remedy; it never invents an amount.
_Avoid_: Recommended action, resolution, payout

**Burden of Proof**:
The Claimant must show their claim is more likely than not. An unproven claim is rejected, and evenly balanced evidence is escalated instead of ruled.
_Avoid_: Benefit of the doubt, tie-break

**Own Finding**:
A point the Judge relies on that neither advocate raised, drawn only from the evidence already in the Case and labelled as such in the Ruling.
_Avoid_: Judge's research, new evidence

**Argument Assessment**:
The Judge's verdict on one argument from a Submission: accepted, rejected, unproven, or not decisive, with a reason. Unproven means the evidence neither establishes nor contradicts it.
_Avoid_: Rebuttal, scoring

**Balance of Evidence**:
The Judge's statement of which way the evidence leans: towards the Claimant, towards the Respondent, or balanced. A balanced Case is escalated.
_Avoid_: Tie, draw

**Policy Gap**:
A situation no Policy Clause covers. The Judge names it in the Ruling and applies the closest clause; it never invents a rule.
_Avoid_: Edge case, loophole

**Confidence**:
A measure of how well the Ruling is supported, built from evidence completeness, consistency, stability, and Policy Fit. It is calculated, not self-reported by the Judge.
_Avoid_: Certainty, probability

**Policy Fit**:
The Judge's assessment of how cleanly the Policy Clauses apply to the facts: clear, arguable, or unclear. It is the only part of Confidence the Judge supplies.
_Avoid_: Policy score, relevance

**Outcome**:
What each party is told after a ruling: the same ruling, worded for that party.
_Avoid_: Notification, result

**Escalation**:
Referral of a case to a Human Reviewer instead of finalizing the ruling, because confidence was too low or a Review Trigger applied.
_Avoid_: Handoff

**Review Trigger**:
A condition that forces Escalation regardless of confidence, such as a Safety Incident, a balanced Balance of Evidence, a Policy Gap, or a photo that fails an Authenticity Check.
_Avoid_: Flag, alert

**Human Reviewer**:
The person who confirms or overrides an escalated Ruling.
_Avoid_: Support agent (ambiguous with our AI agents), moderator, admin

**Safety Officer**:
The Human Reviewer who takes Safety Incidents. They work the same review queue as every other Human Reviewer, with Safety Incidents always at the front. A Safety Incident reaches them by rule, whatever the Judge's confidence, and is never rejected as unsupported.
_Avoid_: Safety team, escalation officer

**Override**:
A Human Reviewer's decision to replace the Judge's proposed Ruling, recorded with a reason.
_Avoid_: Correction, reversal

**Priority**:
The urgency assigned to a Case when it is filed, which decides its place in the human review queue. Safety Incidents get the highest.
_Avoid_: Severity, SLA level
