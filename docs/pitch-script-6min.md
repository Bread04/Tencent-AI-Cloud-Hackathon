# 6-minute pitch: speaker script and where to click

About 5 minutes 45 seconds. Each beat has **DO** (where to click) and **SAY** (word for word). Facts match the scripted run (`MODEL_PROVIDER=stub`).

## Before you start (not timed)

1. Start a fresh server: `MODEL_PROVIDER=stub uv run uvicorn src.api.demo:app`. The header must read **Scripted replies**.
2. Open two tabs: **Tab A** is the console `http://127.0.0.1:8000/`. **Tab B** is the architecture page `http://127.0.0.1:8000/architecture`.
3. Start on Tab A, with the bar above the dispute list reading **Start the walkthrough**.
4. Fallback if a run fails: add `?recorded=1` to the Tab A address.

---

## Beat 1 · The problem (0:00 – 0:30)

**DO:** Stay on Tab A. Don't click anything.

**SAY:**
"Ryde handles thousands of rider and driver disputes a day, by hand. It's slow, and two support agents can rule differently on the same facts. We built Waypoint. Two advocate agents argue each side from the same evidence, and an impartial Judge rules, with every claim cited. I'll settle one dispute live, then show you the architecture behind it."

---

## Beat 2 · Start the dispute (0:30 – 1:00)

**DO:** On Tab A, click **Start the walkthrough**. It runs **DISP-003**. Point at the **Communication Log** as lines appear.

**SAY:**
"A rider says the driver cancelled after four minutes and charged a SGD 5 no-show fee. This is the Communication Log. It shows decisions and citations, never hidden model reasoning. First, evidence is requested. Ordinary code, not a model, pulls the GPS, chat and fare and works out the numbers. The driver arrived at the pickup point and waited four minutes. Anything missing is marked missing, never guessed."

---

## Beat 3 · Sealed evidence, then both sides argue (1:00 – 2:00)

**DO:** Keep pointing down the log as the next lines appear: *evidence sealed*, *policy retrieved*, then two *submission filed* lines (one per advocate).

**SAY:**
"Next the evidence is sealed. It's frozen under a version ID, so nothing can be added once anyone starts arguing. Policy is retrieved, and both sides get the same rulebook. Then the Rider Advocate and the Driver Advocate each file a Submission. They run in parallel and can't see each other. Each must cite evidence IDs, and each must state the strongest counter-argument against its own side. That's what keeps them honest."

---

## Beat 4 · The Judge rules (2:00 – 3:00)

**DO:** When the Ruling line appears, click the **Ruling** tab. Point at the outcome, the amount, then the **Confidence** parts.

**SAY:**
"The Judge assesses every argument: accepted, rejected, unproven, or not decisive, and cites the evidence and policy clause behind each. The ruling is upheld, with a fee reversal of SGD 5.00. The trip data sets a five-minute free wait and the driver waited four. The amount is recomputed in code, because the model never does money. Confidence is 0.80, the weakest of its parts. The system never knows where the rider was, so one of five checklist items is missing, and the ruling tells you exactly that."

---

## Beat 5 · What each person is told (3:00 – 3:20)

**DO:** Click the **Communication log** tab, then **What each person is told**. Point at the rider's and driver's messages.

**SAY:**
"Each party gets the outcome in their own words. The refund is recommended, never executed. Nothing here moves money."

---

## Beat 6 · The opposite ruling (3:20 – 3:45)

**DO:** Click **Next step**. It runs **DISP-002**. Point at the new outcome, **reject**.

**SAY:**
"Same agents, same policy, opposite result. Here the GPS puts the driver at the pickup for the whole wait, so the claim is rejected. The system follows the evidence, not who filed first."

---

## Beat 7 · The architecture diagram (3:45 – 5:30)

**DO:** Switch to **Tab B** (`/architecture`). Move your cursor across the diagram as you speak, following the order below.

**SAY, part 1 · centre (3:45 – 4:15), cursor on the Case store:**
"Here's the same dispute as a diagram. In the middle is the Case store. Every agent reads from it and writes to it. Agents never message each other, so every write becomes a line in the Communication Log, and the log can't drift from what happened."

**SAY, part 2 · colours (4:15 – 4:50), cursor on the three green boxes, then sweep the amber ones:**
"The three green boxes are the required Core Agents: Rider Advocate, Driver Advocate and Judge. The amber boxes are Supporting Agents, and each names the switch that turns it on. With every switch off, the system still works. Turn on precedent and the Judge sees similar past rulings. Turn on the stability check and it rules twice with the arguments swapped, to catch position bias. Evidence Agents and Image Analysis turn chat and photos into quoted, citable facts. SLA routing sends a safety incident to the front of the queue."

**SAY, part 3 · after the Judge (4:50 – 5:20), cursor on History and Confidence, Escalation, then Human Reviewer:**
"After the Judge fixes the outcome, a code-only step applies the History rules. A party's past disputes never reach a prompt. They can only lower Confidence or ask for a human, never flip the result. Then Escalation checks it. Low Confidence, a failed photo check, or a safety incident makes the ruling a proposal, and it goes to a human reviewer. Safety incidents always go to a person, by rule."

**DO:** Click the **Judge** box so the source lines appear.

**SAY, part 4 (5:20 – 5:30):**
"Clicking a box shows the source code behind it. The grey boxes marked simulated are mock data. Nothing touches real Ryde systems."

---

## Beat 8 · Close (5:30 – 5:55)

**DO:** Stay on Tab B. Nothing to click.

**SAY:**
"When a reviewer overrides a proposal, it becomes a new anonymised Precedent. The next similar dispute is shown it, and the Judge has to cite it or explain why the case differs. To sum up: three required agents that rule both ways across two categories, every exchange visible in the log, a switch for each supporting agent, a person in the loop wherever confidence is low, and nothing simulated passed off as real. Thank you."

---

## If you need to adjust

- **Running long:** skip Beat 6, which saves 25 seconds. Cut the supporting-agent list in Beat 7 part 2 to precedent and safety.
- **Running short:** after Beat 6, click **Next step** to run DISP-008 and say: "A second category. The SGD 5.39 refund is computed in code from the driven route versus the planned one."
- **Don't press ‹ (back) or run DISP-004 or DISP-007 in this short version.** They belong to the longer demo.

## Likely questions

- **Is that a real model?** The header says. This run uses scripted replies so it repeats exactly. Setting `MODEL_PROVIDER` makes the same pipeline call a live model.
- **What stops it inventing things?** Code. A citation that doesn't exist is refused, amounts are computed in code, and a bad reply is sent back twice and then held for a person.
- **Does a rider's history count against them?** The Judge never sees it. It can only lower Confidence afterwards.
