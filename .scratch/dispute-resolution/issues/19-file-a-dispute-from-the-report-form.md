# 19: File a Dispute from the report form

**What to build:** The first step of the workflow, connected end to end. The rider's report form (`prototypes/ryde-report`) and rider app (`prototypes/ryde-app`) submit a filed report to the backend, which validates the Trip and category, creates the Case and runs it. The presenter can start a Dispute from the app instead of only picking a prepared one. The report keeps the original submission unchanged and the app shows the Case and its Communication Log when the run finishes.

**Blocked by:** 18, 07

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Braedon (API) and Kyven (form)

- [ ] A report submitted from the form creates a Case on the backend and shows its Ruling and log
- [ ] An unknown Trip or an unsupported category is rejected with a clear error shown in the form
- [ ] The original report is stored unchanged alongside the Dispute
- [ ] Everything shown is labelled as simulated
- [ ] The end-to-end path works with the stub and with no network access
