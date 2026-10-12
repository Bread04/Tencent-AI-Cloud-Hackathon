# 20: Evaluation harness over the mock cases

**What to build:** A small runner that runs every mock case through the system and compares the Ruling with its separate expected-outcome label, then shows a table: case, expected outcome, actual outcome, Confidence, and pass or fail, with an overall pass rate. It reads the evaluation labels (which the agents never see) only after the Case is ruled. Results from the stub prove only that the pipeline is wired; results from the real model are the ones worth showing.

**Blocked by:** 04, 05, 08

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Braedon

- [x] Running the harness produces one row per mock case with expected and actual outcome (`src/evaluation/__init__.py`; five cases today: DISP-002 to DISP-006)
- [x] The labels are read only by the harness, never by an agent or in a prompt (labels load only after a case is ruled, tested; a test fails if any label text or label field name appears in a prompt)
- [x] A page or slide shows the table and the pass rate (`/evaluation` in the console, with a Run button; also `uv run python -m scripts.evaluate`)
- [x] The table says whether the stub or the real model produced it (the report carries the model label, and the page says what a stub result does and does not prove)
- [x] A regression in any mock case's outcome shows as a failure (a wrong outcome, a missing review, an unaccepted trigger, a turned-away case or a missing label each fail a row and lower the pass rate; the script exits 1 on any failure)

**How a case passes:** its outcome, remedy and amount match the label; a case labelled for review must be held, for an accepted reason; a case labelled to resolve must not be held. An ambiguous case has no outcome to match and passes by being held for an accepted reason. A case turned away at intake, or with no label, fails.
**Run it:** `uv run python -m scripts.evaluate` uses `.env` (the scripted stub by default). The console page runs on the same model as the header badge.
**Evaluation switches:** SLA routing is turned on for the run, because Safety Incidents are only resolvable with it. Precedent and the stability check stay as configured (off).
