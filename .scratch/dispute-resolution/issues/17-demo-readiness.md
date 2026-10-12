# 17: Demo readiness

**What to build:** Everything needed to present. A clean architecture diagram, built from the chart in the architecture doc, showing the Case store in the middle, the three Core Agents highlighted, the Supporting Agents as switchable layers, the human review path and the Communication Log, with simulated parts marked. A demo script that opens by naming the Ryde case study, shows the Core Agents alone, then switches on each Supporting Agent that is finished. Switch toggles in the UI so this can be done live. One case ruled for the Claimant and one for the Respondent. Setup instructions so a judge can run the project.

**Blocked by:** 06, 07, 08, 20

**Status:** ready-for-agent

**Tier:** wrap-up · **Owner:** Braedon

- [ ] The architecture diagram exists and marks simulated components
- [ ] The demo script names the Ryde case study at the start
- [ ] The script shows one case ruled for the Claimant and one for the Respondent
- [x] Supporting Agents can be switched on and off from the UI (console checkboxes, table in `src/api/demo_switches.py`)
- [ ] Only finished tiers appear in the demo
- [x] The README explains how to install and run the project
- [ ] The walkthrough has been rehearsed end to end twice
- [x] No credentials are in the repo (`.env` is git-ignored; checked 13 Oct 2026)
