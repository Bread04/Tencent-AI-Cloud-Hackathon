# 14: Photo findings as evidence

**What to build:** Image Analysis. A photo attached to a Dispute becomes evidence with three findings: what the photo shows (for example a stain on the rear seat), whether its capture time falls inside the Trip (reported as unknown when the photo has no metadata), and a signal of whether it shows signs of AI generation. Each finding states its uncertainty. These are signals, never proof. If the image model is unavailable, the photo is recorded as unanalysed and the Case carries on. It is behind a switch.

**Blocked by:** 08

**Status:** done (Braedon, 13 Oct 2026)

**Tier:** 3 · **Owner:** Kyven

- [x] A photo produces Evidence Items for its description, timestamp alignment and AI-generation signal
- [x] Every finding carries a stated uncertainty
- [x] Timestamp alignment is computed by code from metadata and is "unknown" when metadata is missing
- [x] Mock photos exist: one genuine and in the Trip window, one from a different date, one that should fail the AI-generation check
- [x] With the image model unavailable, the photo is recorded as unanalysed and the run continues
- [x] Photo findings appear in the Communication Log
- [x] Tests run on a scripted image stub with no network access
- [x] With the switch off, photos are stored but not analysed

**Built:** `src/tools/photos.py` (capture time from a sidecar `<photo>.json`, the mock stand-in for EXIF; alignment is `aligned`, `outside_window` or `unknown`, with 30 minutes' slack), `src/agents/image_analysis.py` (per photo: `EV-PHOTO-n-DESC`, `-TIME`, `-AI`, each with `derived.uncertainty`; a failed model leaves one `missing` `EV-PHOTO-n` saying unanalysed), orchestrator step behind `switches.image_analysis` before sealing, one `photo_analysed` log row per photo. Mock photos in `data/photos/` are plain placeholder images; what they "show" and whether they look generated is scripted, not real vision. Not done: a console switch and recordings (no prepared Dispute has photos yet; ticket 15 brings the first), and the Judge does not yet lower Confidence on a failed check (ticket 15).
