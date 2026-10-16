# 6-minute pitch script: how a dispute is settled

Spoken at about 135 words a minute, so the spoken text is roughly 780 words, or 5 minutes 45 seconds. Bold lines in brackets are what you do on screen. Facts and numbers come from `docs/demo-script.md` and `docs/architecture.md` and match the scripted run (`MODEL_PROVIDER=stub`).

**Setup:** two tabs open, `/architecture` and the console `/`, plus `/review`. Fresh server. Header reads "Scripted replies". Use the walkthrough bar's **Start the walkthrough** and **Next step**.

---

## 0:00 – 0:35 · The problem (no clicks)

> Ryde handles thousands of rider and driver disputes a day, by hand. It's slow, and two agents can rule differently on the same facts. We built Waypoint: two advocate agents argue each side from the same evidence, and an impartial Judge rules, with every claim cited and the reasoning visible. I'll show you one dispute being settled, and then the architecture that makes the result trustworthy.

## 0:35 – 3:15 · Settling one dispute: DISP-003

**[Console tab. Press "Start the walkthrough". It runs DISP-003. Let the Communication Log fill in.]**

> A rider says the driver cancelled after four minutes and charged a SGD 5 no-show fee. Watch the Communication Log. It shows decisions and citations, not hidden model reasoning.

> **One.** Evidence is requested. Ordinary code, not a model, pulls the GPS, chat and fare, and computes the numbers: the driver arrived at the pickup point and waited four minutes. If something is missing, it is marked missing. It is never guessed.

> **Two.** The evidence is *sealed*. It's frozen under a version ID, so nothing can be added after anyone starts arguing.

> **Three.** The policy is retrieved. Both advocates and the Judge get the same rulebook.

> **Four.** The Rider Advocate and the Driver Advocate each file a Submission. They run in parallel and can't see each other. Each must cite evidence IDs, and each must state the strongest counter-argument against its own side. That's what keeps them honest.

> **Five.** The Judge assesses every single argument: accepted, rejected, unproven, or not decisive. It cites the evidence and the policy clause behind each one.

**[Open the Ruling tab. Point at the amount and the Confidence parts.]**

> The ruling: upheld, fee reversal of SGD 5.00. The trip's own data sets a five-minute free wait, and the driver waited four. The amount is recomputed in code, and the model never does money or Confidence. Confidence is 0.80, the *weakest* of its components. The system never knows where the rider was, so one of five checklist items is missing. The Ruling tells you exactly why.

**[Open "What each person is told".]**

> Each party gets the outcome in their own words. The refund is *recommended*, never executed.

## 3:15 – 3:45 · It can rule either way

**[Press "Next step" for DISP-002.]**

> Same agents, same policy, opposite result. Here the GPS shows the driver at the pickup the whole wait, so the claim is rejected. The system follows the evidence, not who filed first.

## 3:45 – 5:30 · The architecture diagram

**[Switch to the `/architecture` tab. Trace with the cursor from left to right, as you speak.]**

> Here's the same dispute as a diagram. Three things matter.

> **First, the Case store in the middle.** Every agent reads from it and writes to it. Agents never message each other, so every write is a line in the Communication Log. The log can't drift from what really happened.

> **Second, the colours.** The three green boxes are the required Core Agents: the Rider Advocate, the Driver Advocate and the Judge. The amber boxes are the Supporting Agents, and each one names its switch. With every switch off, the system still works. Turn on precedent, and the Judge sees similar past rulings. Turn on the stability check, and it rules twice with the arguments in swapped order, to catch position bias. Turn on Evidence Agents and Image Analysis, and chat and photos become quoted, citable facts. Turn on SLA routing, and a safety incident jumps the queue.

> **Third, what happens after the Judge.** Look at the right side. Once the outcome is fixed, a code-only step applies the History rules. A party's past disputes never enter a prompt. They can only *lower* Confidence or ask for a human, and can never flip the result. Then Escalation checks: low Confidence, a failed photo check, or a safety incident means the ruling is a *proposal*, and goes to a human reviewer. Safety incidents always go to a person, by rule.

**[Click one box, such as Judge, to show the source lines.]**

> Clicking a box shows the source lines behind it. And the grey boxes marked "simulated" are mock data. Nothing here touches real Ryde systems or moves money.

## 5:30 – 6:00 · Close the loop and sum up

**[If time allows, mention rather than show:]**

> If the reviewer overrides a proposal, that becomes a new anonymised Precedent. The next similar dispute is shown it, and the Judge has to cite it or explain why this case differs. Policy text is never silently rewritten.

> To sum up: three required agents that rule both ways across two categories, every exchange visible in the log, a switch for each supporting agent, a person in the loop wherever confidence is low, and nothing simulated passed off as real. Thank you.

---

## Timing and cut options

| Section | Time |
| --- | --- |
| Problem | 0:35 |
| DISP-003 settled | 2:40 |
| DISP-002 opposite ruling | 0:30 |
| Architecture diagram | 1:45 |
| Close | 0:30 |

- **Running long:** drop the DISP-002 section (saves 0:30) and shorten the supporting-agent list in the architecture part to precedent and safety.
- **Running short:** after DISP-002, press Next step on DISP-008 and say "a second category: the SGD 5.39 refund is computed in code from the driven versus planned route".
- **Live-demo failure:** add `?recorded=1` to the console URL. It plays saved runs and calls no model.

## Likely questions (one-line answers)

- **Is that a real model?** The header says. This run uses scripted replies so it repeats. The same pipeline calls a live model when `MODEL_PROVIDER` is set.
- **What stops it inventing things?** Code. A citation that doesn't exist is refused, amounts are computed in code, and a bad reply is sent back twice and then held for a person.
- **Does a rider's history count against them?** The Judge never sees it. It can only lower Confidence afterward.
