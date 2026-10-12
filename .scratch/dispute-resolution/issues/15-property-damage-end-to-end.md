# 15: Property Damage resolved end to end

**What to build:** The Property Damage category. Here the driver is the Claimant: a driver files a cleaning-fee claim with photos, and the rider is the Respondent. The Driver Advocate argues the claim and the Rider Advocate defends. The Judge weighs the photo findings as signals. A photo that fails an Authenticity Check, or whose check is unknown, on evidence that matters to the outcome lowers Confidence and escalates the Case; it never decides the Case alone. The Judge can still rule when there are no photos. Photos can be attached in the UI and their findings are shown.

**Blocked by:** 09, 14

**Status:** done (Braedon, 13 Oct 2026)

**Tier:** 3 · **Owner:** Kyven (cases and advocates) and Braedon (Judge, policy, UI)

- [x] A driver can file a Property Damage Dispute with photos, and the Case records the driver as Claimant
- [x] Property Damage clauses (R-07, D-07) are served for the category, and how a cleaning fee is assessed is a recorded code rule (as in ADR 0002)
- [x] Three mock cases exist: genuine damage, a photo from another date, and a photo failing the AI-generation check
- [x] The Ruling is stated as upholding, partially upholding or rejecting the claim of the driver
- [x] A failed or unknown Authenticity Check caps Confidence and escalates the Case
- [x] No Ruling cites a failed Authenticity Check as its sole reason
- [x] A Property Damage case with no photos still gets a Ruling, with lower Confidence
- [x] Photos can be attached in the UI and their findings and uncertainty are displayed
- [x] Earlier categories still resolve

**Built:** Property Damage resolves end to end (DISP-011 genuine damage, DISP-012 photo from another date, DISP-013 AI-looking photo). Rule and decisions in `docs/adr/0005-cleaning-fee-rule-and-photo-checks.md`. Code: `src/tools/evidence/__init__.py` (claim, trip, chat, History), `src/agents/judge/numbers.py` (`cleaning_fee`, `authenticity_problems`, the `authenticity` Confidence component), `src/agents/judge/draft.py` (the amount input and the sole-reason rule), the `authenticity_check` trigger in the Judge, wording in `src/agents/outcomes.py`, the reviewer's override in `src/agents/escalation.py`. The console shows the filed photos and each finding's uncertainty (Evidence tab) and offers the Photo analysis switch only for a Dispute with photos. "Attached in the UI" here means shown, not uploaded: the mock photos are fixed files; uploading from the report form waits for ticket 19. Photo content and the AI-generation signal are scripted in the stub, so none of this has run on a real vision model.
