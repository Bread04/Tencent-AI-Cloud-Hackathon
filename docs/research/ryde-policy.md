# Ryde's published policies (research notes)

_Gathered 10 Oct 2026 to inform the mock policy. Vocabulary follows [GLOSSARY.md](../../GLOSSARY.md)._

**Reliability:** the environment's network policy blocked direct access to `help.rydesharing.com`, `ptc.gov.sg` and `lta.gov.sg`, so these findings come from web search snippets of Ryde's help centre and press coverage, not from reading the full pages. Treat figures as indicative and recheck them in the Ryde app or help centre before quoting them on stage. Our mock policy is labelled simulated regardless.

## Findings

| Topic | Ryde's rule (Singapore) | Confidence |
| --- | --- | --- |
| Free cancellation, on-demand trip | Free within **3 minutes of the driver match**. After that, the driver receives a **S$4.50** cancellation fee. | Medium: current help centre snippet |
| Free cancellation, advance booking | Free if cancelled more than **15 minutes before the scheduled time**. | Medium: help centre snippet |
| Waiting fee | **S$4.50** once the driver has waited **more than 3 minutes at the pickup point**. A 2020 Vulcan Post article says 4 minutes and that the driver must be at the pickup point according to GPS data. | Medium: sources disagree on 3 vs 4 minutes; 3 is the newer figure |
| Driver arriving early | A help page asks whether a driver arriving during the rider's grace period reduces that grace period. The title suggests it does not; the content was not read. | Low |
| Fee dispute (waiver request) | Riders appeal through **RydeHELP in the app within 30 days** of the trip. A successful waiver is paid as a **S$6.60 voucher**, not cash. Requests after 30 days are not considered. | Medium: help centre snippet |
| Abuse of the waiting fee | After a rider complained about a "waiting time" charge, Ryde refunded it and said it warns drivers who abuse the waiting-time button. | Medium: press report |
| Reported charges in practice | Press reports cite charges of S$4.30 and S$6.50, so amounts have changed over time. | Low |

## Gaps

Not found, because the full pages could not be read:

- Fare structure: base fare, per-km and per-minute rates, surge, platform fee, tolls and ERP, promo codes.
- How fares are adjusted after a route deviation.
- Cleaning or damage fees charged to riders.
- Safety incident reporting and the code of conduct (pages exist, content not read).
- Differences between RydeX, RydePOOL, RydeHIRE and RydeTAXI.
- LTA or Public Transport Council rules that cap point-to-point fees.

To fill these, add the blocked domains under Allowed domains in the cloud environment's network settings and rerun the research.

## Implications for our mock policy

- **Free-wait timer (contract decision Q3):** Ryde starts the waiting timer when the driver is at the pickup point by GPS; the scheduled time only matters for advance bookings. Proposed rule: on-demand trips count from the GPS-confirmed arrival; advance bookings count from the later of arrival and the scheduled time; a No-Show Charge also requires at least one contact attempt by the driver. Still to decide: whether DISP-002 is on-demand or an advance booking, which decides who wins it.
- **Fee amounts:** use S$4.50 for cancellation and waiting fees to match Ryde.
- **Escalation amount limit (Q6):** a S$30 limit sits well above Ryde's fees and waiver vouchers.
- **Remedy realism:** the 30-day appeal window and voucher-not-cash refund could appear in the policy and in the Outcome wording.

## Sources

- [Ryde Help: Cancellation and Waiting Time Policy](https://help.rydesharing.com/hc/en-us/articles/33362932998937-Cancellation-and-Waiting-Time-Policy)
- [Ryde Help: Cancellation and Waiting Time Policy (older version)](https://help.rydesharing.com/hc/en-us/articles/20244064619161-Cancellation-and-Waiting-Time-Policy)
- [Ryde Help: Cancellation Fee Waiver Request](https://help.rydesharing.com/hc/en-us/articles/18229758389017-Cancellation-Fee-Waiver-Request)
- [Ryde Help: If a driver arrives during the rider's grace period, will the grace period for cancellation be reduced?](https://help.rydesharing.com/hc/en-us/articles/4407761270937-If-a-driver-arrives-during-the-rider-s-grace-period-will-the-grace-period-for-cancellation-be-reduced)
- [Ryde Help: How am I charged under the Policy if I am paying my fare by Cash?](https://help.rydesharing.com/hc/en-us/articles/4408070775193-How-am-I-charged-under-the-Policy-if-I-am-paying-my-fare-by-Cash)
- [Ryde Help: Fares and Charges](https://help.rydesharing.com/hc/en-us/sections/4406764226201-Fares-and-Charges)
- [Ryde blog: Everything you need to know about our new Cancellation & Waiting Time Policy](https://rydesharing.com/everything-you-need-to-know-about-our-new-cancellation-waiting-time-policy/)
- [Vulcan Post on Ryde fees](https://vulcanpost.com/?p=771726)
- [The Independent SG: Ryde passenger charged for trip cancelled by driver](https://theindependent.sg/ryde-passenger-charged-for-trip-cancelled-by-driver/)
