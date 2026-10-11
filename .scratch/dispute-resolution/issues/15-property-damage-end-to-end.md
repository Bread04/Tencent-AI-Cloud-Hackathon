# 15: Property Damage resolved end to end

**What to build:** The Property Damage category. Here the driver is the Claimant: a driver files a cleaning-fee claim with photos, and the rider is the Respondent. The Driver Advocate argues the claim and the Rider Advocate defends. The Judge weighs the photo findings as signals. A photo that fails an Authenticity Check, or whose check is unknown, on evidence that matters to the outcome lowers Confidence and escalates the Case; it never decides the Case alone. The Judge can still rule when there are no photos. Photos can be attached in the UI and their findings are shown.

**Blocked by:** 09, 14

**Status:** ready-for-agent

**Tier:** 3 · **Owner:** Kyven (cases and advocates) and Braedon (Judge, policy, UI)

- [ ] A driver can file a Property Damage Dispute with photos, and the Case records the driver as Claimant
- [ ] Property Damage clauses (R-07, D-07) are served for the category, and how a cleaning fee is assessed is a recorded code rule (as in ADR 0002)
- [ ] Three mock cases exist: genuine damage, a photo from another date, and a photo failing the AI-generation check
- [ ] The Ruling is stated as upholding, partially upholding or rejecting the claim of the driver
- [ ] A failed or unknown Authenticity Check caps Confidence and escalates the Case
- [ ] No Ruling cites a failed Authenticity Check as its sole reason
- [ ] A Property Damage case with no photos still gets a Ruling, with lower Confidence
- [ ] Photos can be attached in the UI and their findings and uncertainty are displayed
- [ ] Earlier categories still resolve
