# 20: Evaluation harness over the mock cases

**What to build:** A small runner that runs every mock case through the system and compares the Ruling with its separate expected-outcome label, then shows a table: case, expected outcome, actual outcome, Confidence, and pass or fail, with an overall pass rate. It reads the evaluation labels (which the agents never see) only after the Case is ruled. Results from the stub prove only that the pipeline is wired; results from the real model are the ones worth showing.

**Blocked by:** 04, 05, 08

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Braedon

- [ ] Running the harness produces one row per mock case with expected and actual outcome
- [ ] The labels are read only by the harness, never by an agent or in a prompt
- [ ] A page or slide shows the table and the pass rate
- [ ] The table says whether the stub or the real model produced it
- [ ] A regression in any mock case's outcome shows as a failure
