# AI usage

A running disclosure of where AI tools were used in this project. Update it as you go, not at the end.

## In the product

- The Rider Advocate, Driver Advocate and Judge are model calls (see `docs/architecture.md` section 5). Tickets 04 and 05 build them; ticket 08 connects the real model.
- Everything the model returns is checked in code before it is used: citations, remedies, amounts and Confidence are not left to the prompt (architecture section 4).
- Until ticket 08, runs use scripted replies (`fixtures/stub/`). Those are hand-written mock data, not model output.

## In building it

- Claude Code (Claude) wrote and reviewed much of the code, tests and tickets under the team's direction. Every change was run against the test suite before it was committed.
- The architecture diagram and the walkthrough diagram (`docs/diagrams/`) were authored by Claude Code with the open-source Archify skill, from `docs/architecture.md` and the running code. The demo script (`docs/demo-script.md`) was drafted by Claude Code. Both are to be checked and rehearsed by the team.
- Fill in: which parts each of you wrote or edited by hand, and any other AI tools used (design, research, slides).

## Design sources

- The console's pipeline stepper and Confidence gauge are ported to plain HTML, CSS and JavaScript from two public 21st.dev components: Animated Progress Stepper (shadcnspace/stepper-03) and Financial Score Cards (designali-in/financial-score-cards). The code was retrieved through the 21st MCP and rewritten, not copied in.
- Layout, colours and fonts come from the Waypoint rider-app prototype in `prototypes/`.

## Data

- All trips, evidence and policy are mock data and labelled as simulated. No real Ryde data is used.
