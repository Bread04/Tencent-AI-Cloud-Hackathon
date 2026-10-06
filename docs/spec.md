# Spec: Multi-Agent Autonomous Dispute Resolution

_Triage label to apply when pasted into GitHub Issues: `ready-for-agent`. Vocabulary follows [GLOSSARY.md](../GLOSSARY.md); team split and timeline are in [dev-guide.md](dev-guide.md)._

## Problem Statement

Ryde's support teams resolve thousands of rider-driver Disputes a day by hand. A human agent reviews GPS telemetry, chat logs, fare records and company policy before ruling, so resolution takes 24 to 72 hours, rulings are inconsistent between agents, support hours cost millions, and riders who feel unfairly treated leave the platform.

From a rider's or driver's point of view: they file a Dispute and wait days for a decision they cannot see the reasoning behind. From a support lead's point of view: they cannot trust that similar cases get similar rulings. From a hackathon judge's point of view: they need to see an autonomous system actually gather evidence, argue both sides, and rule, and they need to see how the agents exchange information.

## Solution

An autonomous multi-agent system that takes a filed Dispute and, without human intervention, produces a fair, explained Ruling. A Rider Advocate and a Driver Advocate each gather evidence from the same trip records, apply company policy, and submit an independent Submission. A Judge reads both Submissions against the underlying evidence and policy and issues a Ruling that uphold, partially uphold or reject the claimant's claim, with a recommended action, amount where applicable, cited Evidence Items and Policy Clauses, a reasoning summary that explicitly accepts or rejects each side's arguments, and a Confidence score. Both parties receive the same Ruling, worded for them. A live Communication Log shows every evidence request, Submission and the Ruling.

The target is every agent and capability described in `workflow.md` except the Fraud and Bad-Faith Detection Agent: the three Core Agents, Rider and Driver Evidence Agents, a Policy & Precedent Agent, Image Analysis with Authenticity checks, an Escalation Protocol, an SLA & Routing Manager and a Learning Feedback Loop. It covers all four Dispute Categories: Route Deviation, No-Show Charge, Property Damage and Safety Incident. Delivery is tiered (see Further Notes) so that the required MVP, the three Core Agents resolving Route Deviation and No-Show Charge end to end, is always working before the next layer is added. All data, policy and financial actions are simulated and labelled as such.

## User Stories

### Rider filing and understanding a dispute

1. As a rider, I want to file a Dispute against a specific trip with a plain-language description and the remedy I want, so that I do not have to explain my situation to a support agent.
2. As a rider, I want to choose or have detected the Dispute Category (route deviation or no-show charge), so that the right evidence and policy are examined.
3. As a rider, I want the system to reject a Dispute with a clear message when the trip reference or category is invalid, so that I know what to fix.
4. As a rider, I want my Dispute resolved in minutes rather than days, so that I am not left waiting for my money back.
5. As a rider, I want the Outcome to say whether my claim was upheld, partially upheld or rejected, so that I understand the result at a glance.
6. As a rider, I want to see the refund or fee-reversal amount and how it was calculated, so that I can check it is right.
7. As a rider, I want the Outcome to explain why each of my arguments was accepted or rejected, so that a rejection does not feel arbitrary.
8. As a rider, I want the Outcome to cite the evidence and the policy rules behind the Ruling, so that I can see it is grounded in facts, not opinion.
9. As a rider, I want to see the Confidence of the Ruling, so that I know how firm the decision is.
10. As a rider whose claim is rejected, I want the explanation to be respectful and specific about what the records show, so that I do not feel accused.
11. As a rider, I want the evidence collected for my case to include the records that favour me, so that I am represented fairly even if I did not know what to submit.

### Driver being heard

12. As a driver, I want a Driver Advocate to defend me using the same trip records the rider's side sees, so that I am judged on the same facts.
13. As a driver, I want to add an optional written statement to the case, so that I can give context the records do not show.
14. As a driver, I want my chat messages and call attempts counted as evidence of contact, so that I get credit for trying to reach the rider.
15. As a driver, I want my arrival, waiting and cancellation timestamps to be used as evidence, so that a no-show charge is judged on facts.
16. As a driver, I want a proper detour or rider-requested route change to be considered, so that I am not penalised for following the rider's instructions.
17. As a driver, I want to receive the same Ruling as the rider, worded for me, so that there is one consistent decision.
18. As a driver, I want to see which of my arguments were accepted or rejected and why, so that I can understand and trust the process.
19. As a driver with a strong record, I want my history treated as context only, so that it helps my credibility but is not the sole reason I win.

### Evidence gathering

20. As an advocate agent, I want to retrieve GPS and telemetry for the trip, so that I can show route, stops, pickup arrival and duration.
21. As an advocate agent, I want the actual route distance compared with the optimal route distance, so that a route deviation claim can be measured.
22. As an advocate agent, I want expected versus actual trip duration, so that delay caused by a detour can be quantified.
23. As an advocate agent, I want unexpected stops identified in the trace, so that they can be cited as evidence.
24. As an advocate agent, I want the driver's arrival time compared with the scheduled pickup time and the free-wait and no-show timers, so that a no-show charge can be checked against policy.
25. As an advocate agent, I want chat and call records for the trip, so that agreements, route requests and contact attempts can be cited.
26. As an advocate agent, I want the fare breakdown including base fare, surge and promo, so that the disputed amount can be validated and a remedy calculated.
27. As an advocate agent, I want rider and driver history (prior disputes, ratings, account age), so that context can be offered for the Judge to weigh.
28. As an advocate agent, I want every Evidence Item to carry an ID, source, trip, timestamp and retrieval status, so that I can cite it precisely.
29. As an advocate agent, I want missing evidence recorded as missing rather than assumed, so that my case never relies on invented facts.
30. As an advocate agent, I want conflicting evidence labelled as conflicting, so that the Judge can resolve it openly.
31. As an advocate agent, I want both advocates to read the same underlying records, so that neither side has information the other lacks.

### Policy

32. As an advocate agent, I want to look up the Policy Clauses relevant to the Dispute Category, so that my arguments are grounded in company rules.
33. As an advocate agent, I want every Policy Clause to have a stable ID, so that I can cite it and the citation stays valid if wording improves.
34. As a Judge, I want to look up policy from the same version the advocates used, so that all three agents apply the same rules.
35. As a product owner, I want ambiguous policy points (for example, whether the free wait counts from arrival or from the scheduled time) resolved explicitly in the mock policy, so that rulings are predictable.
36. As a hackathon judge, I want mock policy clearly labelled as simulated, so that it is not mistaken for Ryde's real policy.

### Case building and judging

37. As a Rider Advocate, I want to build an independent Submission stating the rider's claim, the relevant facts, the counter-evidence I anticipate, the requested outcome and the policy cited, so that the rider's position is fully presented.
38. As a Driver Advocate, I want to build an independent Submission stating the driver's defence in the same structure, so that the Judge can compare like with like.
39. As a Judge, I want to compare both Submissions against the underlying evidence rather than only each other's claims, so that a persuasive but unsupported argument does not win.
40. As a Judge, I want to apply the cited Policy Clauses and calculate any remedy amount, so that the Ruling is consistent with policy.
41. As a Judge, I want to explicitly accept or reject each material argument with a reason, so that the Ruling rebuts what it does not agree with.
42. As a Judge, I want to treat user history as context that can adjust Confidence but never as the sole reason for a Ruling, so that the system is fair to users with imperfect records.
43. As a Judge, I want to express Confidence reflecting evidence completeness, consistency and policy fit, so that weak cases are visibly less certain.
44. As a Judge, I want to reduce Confidence when material evidence is missing or conflicting, so that incomplete cases are not presented as certain.
45. As a Judge, I want to rule for the rider when the evidence supports the rider, and for the driver when it supports the driver, so that the system is demonstrably impartial.

### Outcome and transparency

46. As a rider or driver, I want the Outcome to distinguish a recommended refund from one that has actually been executed, so that I do not assume money moved when it did not.
47. As a hackathon judge, I want a live Communication Log showing evidence requests, evidence responses, both Submissions and the Ruling, so that I can see how agents exchange information.
48. As a hackathon judge, I want the log to show decisions and citations rather than hidden model reasoning, so that it is clear and auditable.
49. As a hackathon judge, I want to see both parties' Outcome views side by side, so that I can confirm they get the same decision.
50. As a hackathon judge, I want to open a Case and see its Evidence Items, Submissions, Ruling and log together, so that I can audit the whole decision.
51. As a presenter, I want to select a prepared mock Dispute and run it live in one click, so that the demo is reliable.
52. As a presenter, I want at least one case ruled for the rider and one for the driver, so that the demo shows the system is not biased.
53. As a presenter, I want all simulated data, policy and financial actions labelled on screen, so that the demo is honest about what is real.

### Reliability and development

54. As a developer, I want the model behind a single replaceable adapter with an offline stub, so that I can build and test without network or credits.
55. As a developer, I want the evidence calculations (route distance, wait time) to be deterministic, so that numbers are right and demos repeatable.
56. As a developer, I want the Judge callable on its own from fixture Submissions, so that the Judge can be built before the advocates exist.
57. As a developer, I want sample Submission and Communication Log fixtures committed early, so that two people can work in parallel without blocking each other.
58. As a developer, I want mock cases to carry an expected outcome as a separate evaluation label that agents never see, so that the system cannot read the answer key.
59. As a developer, I want the shared Case contract to change only with both teammates' agreement, so that parallel work does not break.
60. As a presenter, I want the system to fail visibly with a clear error if the model is unreachable, so that a demo problem is obvious.

### Supporting agents (tiered)

61. As a Rider Advocate, I want a Rider Evidence Agent to collect and organise the evidence relevant to the rider's claim, so that I spend my effort arguing, not retrieving.
62. As a Driver Advocate, I want a Driver Evidence Agent to do the same for the driver's defence, so that both sides are equally well prepared.
63. As a Judge, I want the Policy & Precedent Agent to return similar past rulings alongside the policy clauses, so that rulings stay consistent across similar cases.
64. As a Judge, I want precedent treated as advisory, so that an old ruling never overrides the evidence in front of me.
65. As a product owner, I want the same policy source and version served to both advocates and the Judge, so that all three apply identical rules.
66. As a rider, I want a low-Confidence Ruling to go to a human reviewer instead of being finalized, so that doubtful cases are not decided by guesswork.
67. As a rider or driver, I want to be told that my Case is under human review, so that I know a decision is coming and why it is delayed.
68. As a human reviewer, I want a review package with both Submissions, the evidence, the policy references, the proposed Ruling and the reason for review, so that I can decide without redoing the investigation.
69. As a human reviewer, I want to confirm or override the proposed Ruling and record a reason, so that my decision is auditable.
70. As a support lead, I want Safety Incidents fast-tracked and always routed for review, so that the most serious cases are handled first.
71. As a support lead, I want the review queue ordered by priority (urgency and value), so that the most important Cases are reviewed first.
72. As a driver, I want to submit photos with a property-damage claim, so that I can document the mess.
73. As a Judge, I want an Image Analysis finding of what a photo shows, so that I can weigh a damage claim against the evidence.
74. As a Judge, I want an Authenticity check on whether a photo's timestamp aligns with the Trip, so that a photo from another day does not count.
75. As a Judge, I want a signal on whether a photo shows signs of AI generation, with stated uncertainty, so that suspicious photos reduce Confidence without being treated as proof.
76. As a rider, I want a photo that fails authenticity checks to trigger review rather than an automatic ruling against me, so that an uncertain detector cannot decide my case alone.
77. As a Judge, I want to rule normally when no photos exist, so that missing photos do not block a Case.
78. As a support lead, I want a human override captured with its reason and added to the precedent store, so that the system improves from corrections.
79. As a Judge, I want overrides to appear as new precedent for later similar Cases, without silently rewriting policy, so that learning is controlled.
80. As a hackathon judge, I want to turn each supporting agent on or off in the demo, so that I can see the Core Agents work alone and then see what each layer adds.

## Implementation Decisions

- **Architecture.** Agents are plain classes calling a model and tools; no agent framework. Three Core Agents (Rider Advocate, Driver Advocate, Judge) form the required MVP. Around them sit supporting agents: a Rider Evidence Agent and a Driver Evidence Agent that run the deterministic evidence tools and hand structured Evidence Items to their advocate; a Policy & Precedent Agent that serves one shared policy source and past rulings to both advocates and the Judge; an Image Analysis Agent with Authenticity checks (AI-generation indicators and trip-timestamp alignment) for photos; an Escalation Protocol Agent; an SLA & Routing Manager; and a Learning Feedback Loop. Where the whiteboard draws separate policy agents per side, they are implemented as roles over one shared policy source. Each supporting agent can be switched off without breaking the Core Agents.
- **Dispute Categories.** Route Deviation and No-Show Charge are rider-filed. Property Damage (a cleaning-fee claim) is driver-filed and brings in photos and Image Analysis. Safety Incident exercises SLA fast-tracking and escalation. Either party can be the Claimant.
- **Pipeline.** A Dispute is validated; a Case is created; both advocates gather evidence and independently build a Submission; the Judge reviews both and issues a Ruling; each party receives an Outcome; the Case and its Communication Log are retained.
- **No interactive missing-details loop.** Intake validates the trip reference and Dispute Category and rejects invalid input with a clear error.
- **Independent advocates, rebuttal in the Ruling.** The advocates do not see each other's Submission. The Judge's Ruling explicitly accepts or rejects each side's material arguments. No extra advocate round trip.
- **Claimant and Respondent.** A Case records who filed. Each advocate stays tied to its party. A Ruling is always stated as upholding, partially upholding or rejecting the claimant's claim.
- **Shared Case contract.** One contract defines the Case, Evidence Item, Submission, Ruling and Communication Log event. It is agreed jointly and changed only with both teammates' approval.
- **Evidence Item.** Carries an ID, source, trip association, timestamp where available, and a retrieval status of available or missing. Conflicts are labelled.
- **Evidence tools (deterministic).** GPS and telemetry (including actual versus optimal route and unexpected stops), chat and communication, fare breakdown, and rider and driver history. Calculations are plain code, not model calls. Both advocates call the same tools so they read the same records.
- **Policy tool.** One shared mock policy with stable Policy Clause IDs and one version. Advocates and the Judge call it with a role. The ambiguity between the free-wait and no-show thresholds is resolved explicitly in the policy text.
- **Ruling.** Contains: outcome (uphold, partially uphold, reject the claimant's claim), recommended action, amount and currency where applicable with its calculation, cited Evidence Item IDs, cited Policy Clause IDs, a per-argument acceptance or rejection with reasons, a reasoning summary, and a Confidence between 0 and 1 reflecting evidence completeness, consistency and policy fit. The exact Confidence scale and any escalation threshold are fixed in the contract session.
- **Outcome.** Both parties receive the same Ruling worded for each. A recommended action is distinguished from an executed one; financial actions are simulated.
- **History as context.** Rider and driver history may adjust Confidence or inform the reasoning, but is never the sole stated basis for a Ruling.
- **Communication Log.** Records evidence requests and responses, both Submissions, policy references and the Ruling's summary. It shows decisions and citations, not private model reasoning.
- **Model adapter.** All model calls go through one replaceable function. An offline stub implements it for development and tests; the production implementation targets an OpenAI-compatible endpoint, with the provider to be confirmed. Image Analysis needs a model that accepts images, so provider choice must also cover that.
- **Mock Data.** At least three simulated cases per category: one the claimant should win, one the respondent should win, and one genuinely ambiguous case that should end in a partial Ruling with lower Confidence. Property Damage cases include photos, among them one that should fail authenticity checks. Each carries an expected outcome as a separate evaluation label never exposed to the agents. The DISP-002 sample is used as the schema template, with its internal inconsistencies (logged speeds not matching GPS positions, rider's waiting claim, ambiguous wait thresholds) fixed in a copy, not in the original.
- **Interfaces and delivery surface.** A backend exposing case listing and case run operations, and a web interface with a Dispute selector, a live Communication Log, both parties' Outcome views and a Ruling card. All simulated elements are labelled on screen.
- **Ownership split.** The pipeline split in the dev guide still holds for the Core Agents: Kyven builds the cases (model adapter, evidence tools and agents, both advocates, orchestrator, mock cases); Braedon rules and presents (policy, Judge, backend operations, web interface and log view, architecture diagram, demo script). The new supporting agents must be assigned between the two before tickets are cut. The dev guide's ownership table and timeline need updating for the wider scope.
- **Escalation Protocol.** A Ruling below a Confidence threshold, or one triggered by a review rule (for example a Safety Incident), is not finalized. The Escalation Protocol Agent assembles a review package (both Submissions, evidence, policy references, the proposed Ruling and the reason for review) and places the Case in a human review queue. Both parties are told review is pending. A human reviewer confirms or overrides the Ruling, with a recorded reason.
- **SLA & Routing Manager.** Sets a priority when a Dispute is filed (urgency and value, with Safety Incidents fast-tracked) and orders the human review queue by it.
- **Policy & Precedent.** Holds the mock policy, with stable Policy Clause IDs, and a store of past rulings. For a Case it returns the relevant clauses and similar past rulings so the Judge can stay consistent. Precedent is advisory, not binding.
- **Learning Feedback Loop.** A human override is captured with its reason and added to the precedent store, so later similar Cases see it. Updates are controlled: an override is stored as a new precedent, never silently rewriting policy.
- **Image Analysis and Authenticity.** For photo evidence, the Image Analysis Agent assesses what the photo shows (for example damage or mess) and the Authenticity checks report two signals: whether the photo's timestamp aligns with the Trip, and whether it shows signs of AI generation. Findings are signals with stated uncertainty, never proof by themselves, and they lower Confidence or trigger Escalation rather than deciding a Case alone. The Judge must be able to rule without photos when none exist.

## Testing Decisions

- **A good test asserts external behaviour only,** not which function called which or what a prompt contained.
- **Seam 1, the main one:** resolving a Dispute end to end on Mock Data with the model replaced by a scripted stub. Tests assert that the Case contains a well-formed Ruling; every cited Evidence Item and Policy Clause ID exists; the Communication Log contains the evidence requests and responses, both Submissions and the Ruling; missing evidence stays marked missing; and known cases produce the expected outcome (including one for the rider and one for the driver in each category). Deterministic evidence calculations are covered through this seam by checking the evidence they produce.
- **Seam 2, the team boundary:** the Judge called directly with a Case and hand-written fixture Submissions, asserting the same Ruling properties. This lets the Judge be built and tested before the advocates exist.
- **The new agents are tested through the same two seams.** Escalation, SLA priority, precedent use, the learning loop and Image Analysis show up as behaviour of a resolved Case: a low-Confidence case ends pending review, a Safety Incident is prioritised, a stored override influences a later similar Case, and a photo that fails authenticity does not decide a Case alone. Image Analysis uses a scripted stub, like the model.
- **Each supporting agent is tested switched on and switched off,** to prove the Core Agents still resolve Cases without it.
- **The model adapter is the substitution point, not a tested seam.** The stub is scripted per case.
- **Not tested automatically:** individual tools and agents in isolation, and the web interface, which is checked manually before the demo.
- **Prior art:** none; the repository is greenfield.

## Out of Scope

- Fraud and Bad-Faith Detection (dropped by the team). Account history stays context only.
- Per-side policy agents: the whiteboard's three policy agents are one shared policy source with roles.
- The interactive missing-details loop at intake.
- A rebuttal round between advocates; the Judge's Ruling carries the rebuttal.
- Real Ryde systems, real payments, or real policy text; everything is simulated and labelled.
- Authentication, multi-user accounts and production hardening.
- Reliable detection of AI-generated images: Authenticity findings are best-effort signals with stated uncertainty.

## Further Notes

- **Delivery tiers (the cut line).** The scope is ambitious for two people in roughly one weekend plus evenings, so work is ordered and each tier must be working before the next begins. **Tier 0, required MVP:** Rider Advocate, Driver Advocate and Judge resolving Route Deviation and No-Show Charge, with the Communication Log and web interface. **Tier 1:** Escalation Protocol, Policy & Precedent, and the Rider and Driver Evidence Agents. **Tier 2:** SLA & Routing Manager and the Safety Incident category. **Tier 3:** Image Analysis with Authenticity checks and the Property Damage category. **Tier 4:** Learning Feedback Loop. If time runs out, work stops at a tier boundary, so the demo never contains a half-built layer. Everything stays in scope; the order says what is cut first if time runs out.
- **Deadline:** 15 October 2026. Real working time is one weekend (10 to 11 October) plus short evenings, with two people. The recommended timeline and the Sunday 11 October integration day are in the dev guide.
- **Blocking dependency:** the model provider and credentials are not yet confirmed. Work proceeds against the offline stub until a working endpoint exists.
- **Critical path:** mock policy text and mock cases are on the critical path because the agents cannot be written or tested without them.
- **Source documents:** the challenge brief (README), the workflow document, the whiteboard, and the DISP-002 sample dataset. The handbook PDF and sample dataset are intentionally not committed.
- **Open decisions for the contract session:** the Confidence scale and escalation threshold, and the exact fields of each contract entity.
