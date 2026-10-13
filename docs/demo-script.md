# Demo script

The Demo Day walkthrough: what to click, what the audience sees, and what to say. Lines in a quote block are spoken. It runs about eight minutes; three steps are marked as ones you can skip to bring it to about five. The short version never ticks Stability check or Evidence agents, so name them on the diagram instead of showing them.

The whole walkthrough at a glance is [diagrams/demo-walkthrough.html](diagrams/demo-walkthrough.html). The steps here are the same rows as `STEPS` in [`src/api/walkthrough.py`](../src/api/walkthrough.py). A test checks each step here against that table: the Dispute, the switches ticked, the outcome, the amount, the Confidence and Priority figures quoted, the review reasons and the Override's wording. The rehearsal below runs the table end to end.

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
3. Open two browser tabs: the console at `http://127.0.0.1:8000/` and the review queue at `http://127.0.0.1:8000/review`. Keep the console tab open for the whole demo. Its ticked boxes are not saved, so leaving the page and coming back unticks them. If that happens, `http://127.0.0.1:8000/?precedent=1&stability=1&routing=1&evidence=1&learning=1` ticks them again (Photo analysis is ticked by hand once a Dispute with photos is selected).
4. Set **Replay speed** to **Presenter** so the Communication Log fills in at a readable pace. Use **Fast** if you are short of time.
5. Start from a fresh server. Cases, the review queue and learned Precedents live in memory, so a restart clears them.

If runs start failing on the day (for example the header names a live model and it cannot be reached), tick **Replay a recording** in the header. The console then plays saved scripted runs of the same Disputes and calls no model. The server must still be up, because it serves the page. A recording creates no Case, so nothing reaches the review queue: the queue in step 6 and all of steps 10 and 11 need real runs.

## Opening

Show the architecture page (`/architecture`). Clicking a box shows the source lines behind it; the browser's back button returns to the console.

> We chose the Ryde case study from the Digital Native Track: the Multi-Agent Autonomous Dispute Resolution System. A rider or a driver files a dispute, two advocate agents argue each side from the same evidence, and a Judge agent rules, with its reasoning and a confidence score.

> Three things to notice in this diagram. Every agent reads and writes one Case store, so no agent messages another, and every write is a line in the Communication Log. The three green boxes are the required agents. The amber boxes are the Supporting Agents, each naming the switch that turns it on, and we will turn them on one at a time. The grey boxes marked simulated stand in for Ryde's systems: the trips, the policy, the photos and the payments are mock data.

## Part 1: the three Core Agents alone

Open the console tab. Every switch in the header is unticked.

### 1. DISP-003: a No-Show Charge ruled for the Claimant

Click **DISP-003**. The rider says the driver cancelled early and they were charged a no-show fee.

Point at the Communication Log as it fills: evidence requested and sealed, policy retrieved, a Submission from each advocate, then the Judge's assessment and Ruling.

- Ruling: `uphold`, fee reversal of SGD 5.00, Confidence 0.80, final.
- This is the case ruled for the Claimant: the rider filed it and the rider wins.

> The driver waited four minutes. The trip's own data sets a five-minute free wait, so the fee was charged too early. That arithmetic is done in code, not by the model. The Judge accepts or rejects each argument and cites the evidence item and the policy clause behind it.

Open the **Ruling** tab to show the Confidence parts and the per-argument assessment, then **What each person is told** on the Overview tab: the rider and the driver each get their own Outcome, and the refund is marked recommended, never executed.

### 2. DISP-002: the same category ruled for the Respondent

Click **DISP-002**. Another rider disputes a no-show fee.

- Ruling: `reject`, no action, Confidence 0.70, final.
- This is the case ruled for the Respondent: the rider filed it and the driver wins.

> Same agents, same policy, the opposite Ruling. Here the GPS record puts the driver at the pickup point for the whole wait, and the driver tried to reach the rider. The Rider Advocate still argued the rider's side as well as it could. The system follows the evidence, not whoever filed first.

### 3. DISP-008: a Route Deviation with a computed partial refund

Click **DISP-008**. The rider says the driver took a longer route.

- Ruling: `partially_uphold`, partial refund of SGD 5.39, Confidence 0.95, final.

> A second category, end to end, with the same three agents. The refund is not a number the model chose. Code compares the driven route with the planned one and recomputes the fare, and the Ruling shows the calculation.

Open the **Ruling** tab and show the calculation.

## Part 2: the Supporting Agents, one switch at a time

Each switch stays ticked once it is on. Never untick one.

### 4. DISP-003 again, now with precedent

Tick **Use precedent**, then click **DISP-003**.

- A new log event, `Precedent retrieved`, lists three similar past Rulings.
- Ruling: still `uphold`, SGD 5.00, final. The Judge cites PREC-NS-02 and says why the two it departs from are different.

> The Policy and Precedent Agent finds similar past rulings by tags. They are advisory. Evidence and policy come first, and a Ruling that departs from a precedent it was shown must say why, or it is refused.

### 5. DISP-003 once more, with the stability check (can be skipped)

Tick **Stability check**, then click **DISP-003**.

- A new log event, `Stability check`: the Judge ruled twice with the order of the two Submissions swapped.
- Ruling: `uphold`, SGD 5.00, but now a proposal held for a person: `stability_disagreement`.

> Language-model judges can favour whichever argument they read first. So the Judge rules twice with the order swapped. In this prepared case the second pass is scripted to disagree, to show what happens when it does: Confidence drops and a person decides. Nothing is paid on a ruling the system does not trust.

### 6. DISP-005: a Safety Incident jumps the queue

Tick **SLA routing**, then click **DISP-005**. The rider reports dangerous speeding.

- A new log event, `Priority set`. The Case shows Priority 130. A No-Show Case scores 20.
- Ruling: `uphold` as a proposal, held for a person: `safety_incident`.

Switch to the review tab and reload it: DISP-005 is at the top of the queue.

> The SLA and Routing Manager scores every Case by urgency and value. A Safety Incident always goes to a person, however confident the Judge is, and it goes to the front of the review queue with a full review package.

### 7. DISP-011: Evidence Agents read the chat (can be skipped)

Tick **Evidence agents**, then click **DISP-011**. Here the driver is the Claimant, asking for a cleaning fee.

- The log shows a Rider Evidence Agent and a Driver Evidence Agent. Open **Evidence and policy**: new items quote the chat word for word, including the rider's "Sorry, I did spill my drink."
- Ruling: `uphold`, compensation to the driver of SGD 40.00, final.

> Each side gets its own Evidence Agent, which turns messy chat into facts. Every fact must quote the message it came from, and code checks the quote is really there.

### 8. DISP-011 again, with the photo analysed

Tick **Photo analysis**, then click **DISP-011**. The box can only be ticked while a Dispute with photos is selected.

- A new log event, `Photo analysed`. Open **Evidence and policy**: findings for what the photo shows, when it was taken and whether it looks AI-generated, each with its uncertainty.
- Ruling: `uphold`, SGD 40.00, final. A driver's claim, upheld.

> Image Analysis reports what the photo shows, whether its timestamp falls inside the trip, and any sign of AI generation. Those are signals for the Judge, never a Ruling on their own.

### 9. DISP-012: a photo that fails its check (can be skipped)

Click **DISP-012**. Another cleaning-fee claim.

- Ruling: `reject` as a proposal, held for a person: `authenticity_check`.

> Same claim, but this photo was taken two weeks before the trip. The check fails, Confidence is capped, and a person decides. A bad photo never wins or loses a case by itself.

### 10. DISP-004: a person overrides the Judge

Tick **Learn from overrides**, then click **DISP-004**. The driver's GPS stops two minutes after arrival.

- Ruling: `reject` as a proposal, Confidence 0.50, held for a person: `low_confidence`.

Switch to the review tab, reload it and open the DISP-004 Case. Show **Why it is held** and the proposed ruling. Then enter your name, choose **Override: reverse the outcome**, give this reason, and press **Record the decision**:

```
The driver's GPS stops two minutes after arrival, so the full wait is not proven. A no-show fee needs a proven wait.
```

- The Case becomes final for the rider, with a fee reversal of SGD 5.00, and both parties are told.
- The log gains `Review decision` and `Precedent added`.

> When Confidence falls below 0.7 the Ruling is only a proposal. The reviewer sees why it was held, both Submissions and the evidence, and confirms or overrides with a reason. With the Learning Feedback Loop on, that Override becomes a Precedent. Policy text is never changed by it.

### 11. DISP-007: the next similar Case sees the Override

Back on the console tab, click **DISP-007**.

- `Precedent retrieved` now lists PREC-HO-0001, marked as a human override.
- Ruling: `reject`, final. The Judge cites the Override and explains why this Case differs: here the GPS covers the whole wait.

> The Override a person recorded a minute ago is now in front of the Judge. It did not blindly copy it. It cited it and explained why this case is different. That is the loop: the system rules, a person overrides, and the next Ruling takes that Override into account.

After step 10, do not run DISP-002 or DISP-004 again, and keep **Learn from overrides** ticked for DISP-007. They are No-Show Cases, so they are now shown the Override too, and their other scripted Judge replies do not explain a departure from it. The system then refuses the Ruling and holds the Case, which is correct but is not what this script says. Restart the server to clear it.

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
- **Escalation has no checkbox.** It is on for every run, including Part 1, so a low-Confidence Ruling is never sent out as final. Part 1's three Cases are all above the line and are not escalated.
- **Real payments, real Ryde data, messages sent to riders and drivers.** All simulated and labelled as such on every page. Each Outcome is shown on screen, not sent.
