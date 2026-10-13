# 19: File a Dispute from the report form

**What to build:** The first step of the workflow, connected end to end. The rider's report form (`prototypes/ryde-report`) and rider app (`prototypes/ryde-app`) submit a filed report to the backend, which validates the Trip and category, creates the Case and runs it. The presenter can start a Dispute from the app instead of only picking a prepared one. The report keeps the original submission unchanged and the app shows the Case and its Communication Log when the run finishes.

**Blocked by:** 18, 07

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Braedon (API) and Kyven (form)

- [x] A report submitted from the form creates a Case on the backend and shows its Ruling and log
- [x] An unknown Trip or an unsupported category is rejected with a clear error shown in the form
- [x] The original report is stored unchanged alongside the Dispute
- [x] Everything shown is labelled as simulated
- [x] The end-to-end path works with the stub and with no network access

**How it works:** `POST /api/reports` takes the form's report, `src/intake/report.py` turns it into a Dispute (the report is kept as submitted in `filed_report`), and the Case runs in the background. An unknown Trip or a category the workflow cannot resolve (Fare / payment, Lost item, Other) is refused with a 422 and the reason, shown in the form. The report form has a "File this report as a Dispute" button (`prototypes/ryde-app/dispute-panel.js`, `report-dispute.js`) that watches the Case and shows its Ruling and Communication Log. The rider app's Case tab reopens a Dispute filed for that trip; the console nav links to the form. On the stub, a filed report replays the prepared Dispute on the same Trip and category. Not checked: the form in a real browser (Chrome could not reach the local server); the API round trip and the panel's logic are tested.
