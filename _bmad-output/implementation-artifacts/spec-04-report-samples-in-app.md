---
title: 'Ticket 04: report samples in the rider app'
type: 'feature'
created: '2026-10-12'
status: 'done'
route: 'one-shot'
---

# Ticket 04: report samples in the rider app

## Intent

**Problem:** DISP-003 and DISP-004 existed as report datasets but could not be selected in the app or loaded into its report form.

**Approach:** Add curated rider-visible trip records for R-7824 and R-7825 and share their report templates with the report page. Preserve the existing DISP-002 example. The standalone report page offers three samples; a linked report offers only its selected trip's sample. Confirming a report runs the existing Evidence → Policy → Advocate flow and saves the case for the correct rider and trip. Expected outcomes, driver GPS and private histories stay outside the browser data. Call attempts retain their record type. New sample templates leave personal waiting time blank because driver timers do not establish how long the rider waited.

Changing a loaded sample's trip asks before replacing the draft and attachments. Switching to manual entry clears the old sample; switching a new Rider sample to Driver asks before clearing its account of events. Resetting a linked report preserves its rider/trip identity. Cache versions load the updated shared scripts. Tests verify source report parity, ownership, case preparation and sample isolation; browser checks covered standalone and linked creation, return to the app, reset and trip replacement. Verification: 21 prototype tests and 138 backend tests passed. This change does not implement a Judge or process a refund. Incoming Git changes and the staged ticket 03 deletion were left intact.

## Suggested Review Order

- Inspect the rider-visible trip projections and shared sample templates.
  [data.js:1](../../prototypes/ryde-app/data.js#L1)
- Check sample selection, replacement confirmation and report creation.
  [index.html:19](../../prototypes/ryde-report/index.html#L19)
- Verify linked reports stay bound to their selected rider and trip.
  [report-bridge.js:12](../../prototypes/ryde-app/report-bridge.js#L12)
- Keep call attempts distinct from party-authored messages in evidence.
  [rider-evidence-agent.js:31](../../prototypes/ryde-app/rider-evidence-agent.js#L31)
- Review source parity, ownership and existing pipeline integration checks.
  [samples.test.cjs:1](../../prototypes/ryde-app/tests/samples.test.cjs#L1)
- Follow the steps for loading each sample.
  [README.md:14](../../prototypes/ryde-app/README.md#L14)
