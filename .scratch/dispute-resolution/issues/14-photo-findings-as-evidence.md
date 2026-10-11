# 14: Photo findings as evidence

**What to build:** Image Analysis. A photo attached to a Dispute becomes evidence with three findings: what the photo shows (for example a stain on the rear seat), whether its capture time falls inside the Trip (reported as unknown when the photo has no metadata), and a signal of whether it shows signs of AI generation. Each finding states its uncertainty. These are signals, never proof. If the image model is unavailable, the photo is recorded as unanalysed and the Case carries on. It is behind a switch.

**Blocked by:** 08

**Status:** ready-for-agent

**Tier:** 3 · **Owner:** Kyven

- [ ] A photo produces Evidence Items for its description, timestamp alignment and AI-generation signal
- [ ] Every finding carries a stated uncertainty
- [ ] Timestamp alignment is computed by code from metadata and is "unknown" when metadata is missing
- [ ] Mock photos exist: one genuine and in the Trip window, one from a different date, one that should fail the AI-generation check
- [ ] With the image model unavailable, the photo is recorded as unanalysed and the run continues
- [ ] Photo findings appear in the Communication Log
- [ ] Tests run on a scripted image stub with no network access
- [ ] With the switch off, photos are stored but not analysed
