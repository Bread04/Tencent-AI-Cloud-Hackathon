# Demo script

The Demo Day walkthrough: what to click, what the audience sees, and what to say. Lines in a quote block are spoken. It runs about eight minutes; three steps are marked as ones you can skip to bring it to about five. The short version never turns on Stability check or Evidence agents, so name them on the diagram instead of showing them.

The whole walkthrough at a glance is [diagrams/demo-walkthrough.html](diagrams/demo-walkthrough.html). The steps here are the same rows as `STEPS` in [`src/api/walkthrough.py`](../src/api/walkthrough.py). A test checks each step here against that table: the Dispute, the switches turned on, the outcome, the amount, the Confidence and Priority figures quoted, the review reasons and the Override's wording. The rehearsal below runs the table end to end.

## Before you present

1. Start the server on the scripted replies. Every outcome in this script is the scripted one, so the run is the same each time and needs no network.

   ```
   $env:MODEL_PROVIDER = "stub"; uv run uvicorn src.api.demo:app      # PowerShell
   MODEL_PROVIDER=stub uv run uvicorn src.api.demo:app                # bash
   ```

   The header must read **Scripted replies**. If it names a live model, the `.env` file is in charge: stop and start again with the variable set.
2. Rehearse. This runs every step below in order, in one store like the server, and checks how each ends:

   ```
   uv run python -m scripts.rehearse
   ```

   It must end with `11 of 11 steps ended as scripted.`
3. Open two browser tabs: the console at `http://127.0.0.1:8000/` and the review queue at `http://127.0.0.1:8000/review`. Keep the console tab open for the whole demo. The supporting agents that are switched on are not saved, so leaving the page and coming back turns them off. The walkthrough bar above the dispute list turns each one on again as you press **Next step**: step 1 starts from the three core agents, and pressing **‹** goes back a step and turns later agents off with it.
4. The Communication Log fills in at a readable pace by default (`?pace=150` is faster, `?pace=0` is instant). Add `?short=1` to the address to leave out the three steps marked skippable.
5. Start from a fresh server. Cases, the review queue and learned Precedents live in memory, so a restart clears them.

If runs start failing on the day (for example the header names a live model and it cannot be reached), add `?recorded=1` to the address. The console then plays saved scripted runs of the same Disputes and calls no model. The server must still be up, because it serves the page. A recording creates no Case, so nothing reaches the review queue: the queue in step 6 and all of steps 10 and 11 need real runs.

## Opening

Show the architecture page (`/architecture`). Clicking a box shows the source lines behind it; the browser's back button returns to the console.

> We chose the Ryde case study from the Digital Native Track: the Multi-Agent Autonomous Dispute Resolution System. A rider or a driver files a dispute, two advocate agents argue each side from the same evidence, and a Judge agent rules, with its reasoning and a confidence score.

> Three things to notice in this diagram. Every agent reads and writes one Case store, so no agent messages another, and every write is a line in the Communication Log. The three green boxes are the required agents. The amber boxes are the Supporting Agents, each naming the switch that turns it on, and we will turn them on one at a time. The grey boxes marked simulated stand in for Ryde's systems: the trips, the policy, the photos and the payments are mock data.

## Part 1: the three Core Agents alone

Open the console tab. The walkthrough bar reads **Start the walkthrough**. Every supporting agent is off, so the workflow canvas shows only the three core agents lit.

### 1. DISP-003: a No-Show Charge ruled for the Claimant

Press **Start the walkthrough**. It runs **DISP-003**. The rider says the driver cancelled early and they were charged a no-show fee.

Point at the Communication Log as it fills: evidence requested and sealed, policy retrieved, a Submission from each advocate, then the Judge's assessment and Ruling.

- Ruling: `uphold`, fee reversal of SGD 5.00, Confidence 0.80, final.
- This is the case ruled for the Claimant: the rider filed it and the rider wins.

> The driver waited four minutes. The trip's own data sets a five-minute free wait, so the fee was charged too early. That arithmetic is done in code, not by the model. The Judge accepts or rejects each argument and cites the evidence item and the policy clause behind it.

Open the **Ruling** tab to show the Confidence parts and the per-argument assessment, then on the **Communication log** tab, **What each person is told**: the rider and the driver each get their own Outcome, and the refund is marked recommended, never executed.

### 2. DISP-002: the same category ruled for the Respondent

Press **Next step**. It runs **DISP-002**. Another rider disputes a no-show fee.

- Ruling: `reject`, no action, Confidence 0.70, final.
- This is the case ruled for the Respondent: the rider filed it and the driver wins.

> Same agents, same policy, the opposite Ruling. Here the GPS record puts the driver at the pickup point for the whole wait, and the driver tried to reach the rider. The Rider Advocate still argued the rider's side as well as it could. The system follows the evidence, not whoever filed first.

### 3. DISP-008: a Route Deviation with a computed partial refund

Press **Next step**. It runs **DISP-008**. The rider says the driver took a longer route.

- Ruling: `partially_uphold`, partial refund of SGD 5.39, Confidence 0.95, final.

> A second category, end to end, with the same three agents. The refund is not a number the model chose. Code compares the driven route with the planned one and recomputes the fare, and the Ruling shows the calculation.

Open the **Ruling** tab and show the calculation.

## Part 2: the Supporting Agents, one switch at a time

Each supporting agent stays on once a step has turned it on. The workflow canvas lights it up as it works. Never press **‹** during this part.

### 4. DISP-003 again, now with precedent

Press **Next step**. It turns on **Use precedent** and runs **DISP-003**.

- A new log event, `Precedent retrieved`, lists three similar past Rulings.
- Ruling: still `uphold`, SGD 5.00, final. The Judge cites PREC-NS-02 and says why the two it departs from are different.

> The Policy and Precedent Agent finds similar past rulings by tags. They are advisory. Evidence and policy come first, and a Ruling that departs from a precedent it was shown must say why, or it is refused.

### 5. DISP-003 once more, with the stability check (can be skipped)

Press **Next step**. It turns on **Stability check** and runs **DISP-003**.

- A new log event, `Stability check`: the Judge ruled twice with the order of the two Submissions swapped.
- Ruling: `uphold`, SGD 5.00, but now a proposal held for a person: `stability_disagreement`.

> Language-model judges can favour whichever argument they read first. So the Judge rules twice with the order swapped. In this prepared case the second pass is scripted to disagree, to show what happens when it does: Confidence drops and a person decides. Nothing is paid on a ruling the system does not trust.

### 6. DISP-005: a Safety Incident jumps the queue

Press **Next step**. It turns on **SLA routing** and runs **DISP-005**. The rider reports dangerous speeding.

- A new log event, `Priority set`. The Case shows Priority 130. A No-Show Case scores 20.
- Ruling: `uphold` as a proposal, held for a person: `safety_incident`.

The second line of the log, `Sent to a Safety Officer at once`, appears before any evidence is gathered. Switch to the review tab and reload it: DISP-005 is at the top of the queue, and while the Judge is still drafting it shows as awaiting proposal. Open it: the proposal is labelled as a fare remedy only, because the Safety Officer investigates conduct, not this system. The rider is told a Safety Officer has the report as a priority; the driver is told only that a report is under review.

> The SLA and Routing Manager scores every Case by urgency and value. A Safety Incident always goes to a person, however confident the Judge is, and it goes to the front of the review queue with a full review package.

### 7. DISP-011: Evidence Agents read the chat (can be skipped)

Press **Next step**. It turns on **Evidence agents** and runs **DISP-011**. Here the driver is the Claimant, asking for a cleaning fee.

- The log shows a Rider Evidence Agent and a Driver Evidence Agent. Open **Evidence and policy**: new items quote the chat word for word, including the rider's "Sorry, I did spill my drink."
- Ruling: `uphold`, compensation to the driver of SGD 40.00, final.

> Each side gets its own Evidence Agent, which turns messy chat into facts. Every fact must quote the message it came from, and code checks the quote is really there.

### 8. DISP-011 again, with the photo analysed

Press **Next step**. It turns on **Photo analysis** and runs **DISP-011**, which has photos.

- A new log event, `Photo analysed`, with a card under it: the photo beside its three findings, what it shows, whether it was taken during the trip and whether it looks AI-generated, each with its uncertainty. The Photo analysis box on the workflow lights up. **Evidence and policy** has the same findings as citable items.
- Ruling: `uphold`, SGD 40.00, final. A driver's claim, upheld.

> Image Analysis reports what the photo shows, whether its timestamp falls inside the trip, and any sign of AI generation. Those are signals for the Judge, never a Ruling on their own.

### 9. DISP-012: a photo that fails its check (can be skipped)

Press **Next step**. It runs **DISP-012**. Another cleaning-fee claim.

- Ruling: `reject` as a proposal, held for a person: `authenticity_check`.

> Same claim, but this photo was taken two weeks before the trip. The check fails, Confidence is capped, and a person decides. A bad photo never wins or loses a case by itself.

The card in the log shows the failed check in amber. If there is time, click **DISP-013** in the list: its photo was taken during the trip but the card flags it as likely AI-generated, so it is held for a person for `authenticity_check` too. Then press **Next step** to carry on.

### 10. DISP-004: a person overrides the Judge

Press **Next step**. It turns on **Learn from overrides** and runs **DISP-004**. The driver's GPS stops two minutes after arrival.

- Ruling: `reject` as a proposal, Confidence 0.50, held for a person: `low_confidence`.

Switch to the review tab, reload it and open the DISP-004 Case. Show **Why it is held** and the proposed ruling. Then enter your name, choose **Override: reverse the outcome**, give this reason, and press **Record the decision**:

```
The driver's GPS stops two minutes after arrival, so the full wait is not proven. A no-show fee needs a proven wait.
```

- The Case becomes final for the rider, with a fee reversal of SGD 5.00, and both parties are told.
- The log gains `Review decision` and `Precedent added`.

> When Confidence falls below 0.7 the Ruling is only a proposal. The reviewer sees why it was held, both Submissions and the evidence, and confirms or overrides with a reason. With the Learning Feedback Loop on, that Override becomes a Precedent. Policy text is never changed by it.

### 11. DISP-007: the next similar Case sees the Override

Back on the console tab, press **Next step**. It runs **DISP-007**.

- `Precedent retrieved` now lists PREC-HO-0001, marked as a human override.
- Ruling: `reject`, final. The Judge cites the Override and explains why this Case differs: here the GPS covers the whole wait.

> The Override a person recorded a minute ago is now in front of the Judge. It did not blindly copy it. It cited it and explained why this case is different. That is the loop: the system rules, a person overrides, and the next Ruling takes that Override into account.

After step 10, do not run DISP-002 or DISP-004 again, and keep **Learn from overrides** on for DISP-007. They are No-Show Cases, so they are now shown the Override too, and their other scripted Judge replies do not explain a departure from it. The system then refuses the Ruling and holds the Case, which is correct but is not what this script says. Restart the server to clear it.

## Closing

Open `/evaluation` and press **Run the evaluation**.

> Every prepared case has an expected outcome in a file the agents never read. This page runs all twelve and compares. The header says which model produced the result, so a scripted run is never passed off as a live one.

> To sum up: three required agents that rule both ways across two categories, every exchange visible in the log, the supporting agents each behind a switch, a person in the loop wherever confidence is low, and nothing simulated presented as real.

## If you are asked

- **Is that a real model?** The header says. This script runs on scripted replies so it is repeatable. Set `MODEL_PROVIDER=openai_compatible` with the credentials in `.env.example` and the same pipeline calls a real model; the **Model calls** tab then shows each request and reply. Outcomes and Confidence on a live model can differ from the ones written here.
- **What stops the model inventing things?** Code. A citation to evidence or a clause that is not in the Case is refused, amounts are computed in code, and a reply that fails validation is sent back with the error up to twice before the Case is held for a person.
- **Does a rider's history count against them?** The Judge never sees it. A History step runs after the outcome is fixed and can only lower Confidence or add a review trigger.
- **Why no framework?** The order of stages is fixed, so it is ordinary code. Models are used only to read messy text, argue a side and weigh arguments.

## Not in the demo

- **Fraud and Bad-Faith Detection Agent.** Not built. It is the one optional agent in the brief that we left out.
- **Filing a Dispute from the report form into this pipeline** (tickets 18 and 19). Not finished, so do not open the Rider app or the Help form during the walkthrough. The Rider app prepares its own Submission and does not produce a Judge Ruling.
- **Precedent retrieval by embeddings.** The code path exists behind a setting; the demo uses tags, the default.
- **Escalation has no switch.** It is on for every run, including Part 1, so a low-Confidence Ruling is never sent out as final. Part 1's three Cases are all above the line and are not escalated.
- **Real payments, real Ryde data, messages sent to riders and drivers.** All simulated and labelled as such on every page. Each Outcome is shown on screen, not sent.
