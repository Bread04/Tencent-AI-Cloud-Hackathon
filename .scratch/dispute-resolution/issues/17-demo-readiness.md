# 17: Demo readiness

**What to build:** Everything needed to present. A clean architecture diagram, built from the chart in the architecture doc, showing the Case store in the middle, the three Core Agents highlighted, the Supporting Agents as switchable layers, the human review path and the Communication Log, with simulated parts marked. A demo script that opens by naming the Ryde case study, shows the Core Agents alone, then switches on each Supporting Agent that is finished. Switch toggles in the UI so this can be done live. One case ruled for the Claimant and one for the Respondent. Setup instructions so a judge can run the project.

**Blocked by:** 06, 07, 08, 20

**Status:** ready-for-human (built by Braedon, 13 Oct 2026; one box is left for a person: rehearsing the spoken walkthrough)

**Tier:** wrap-up · **Owner:** Braedon

- [x] The architecture diagram exists and marks simulated components (`docs/architecture-diagram.svg`, also at `/architecture` in the app)
- [x] The demo script names the Ryde case study at the start (`docs/demo-script.md`, the first spoken line)
- [x] The script shows one case ruled for the Claimant and one for the Respondent (DISP-003 and DISP-002, with every switch off)
- [x] Supporting Agents can be switched on and off from the UI (console checkboxes, table in `src/api/demo_switches.py`)
- [x] Only finished tiers appear in the demo (every step is run by the rehearsal; the script lists what is left out: the Fraud agent, and filing from the report form, tickets 18 and 19)
- [x] The README explains how to install and run the project
- [ ] The walkthrough has been rehearsed end to end twice (by machine, yes: on 13 Oct 2026 every step was run twice against a fresh server over its HTTP API and ended as scripted. `tests/test_walkthrough.py` now does the same through the API on every test run. By a person clicking and speaking, not yet)
- [x] No credentials are in the repo (`.env` is git-ignored; checked 13 Oct 2026)

**How it works:** the walkthrough is a table, `STEPS` in `src/api/walkthrough.py`: the Dispute, the switches ticked before it, and how it must end. `uv run python -m scripts.rehearse` runs the table in order in one store, like the server, on the scripted replies. `docs/demo-script.md` is the same steps with the clicks and the words; `tests/test_walkthrough.py` fails if the two disagree. The short version leaves out the steps marked skippable, and is tested too.
**Found while rehearsing:** after the Override in step 10, DISP-002 and DISP-004 run with Use precedent ticked are held with `stage_failed` (so is DISP-007 if Learn from overrides is unticked). They are served the new Override, and their scripted Judge replies do not explain departing from it, so the Ruling is refused. It is the scripts that are short, not the system; the script says to restart the server instead of running them again. Also, 80 of the 240 recorded streams (most of those with Stability check on) held a run that had failed for want of a scripted second-pass reply, because the recorder used a plainer stub than the demo; the recorder now uses the demo's own and those 80 were re-recorded. The console header also pushed its last switches off screen below about 1,850 pixels wide; it now wraps.
**Not checked:** the walkthrough on a live model (no live calls were made for this ticket), and a click-through in a real browser (pages were checked in headless Chrome screenshots).
