# The cleaning fee is a code rule, and photo checks only cap Confidence

Approved for the simulated Ticket 15 cases. Policy clauses R-07 and D-07 are unchanged: they say a report alone does not establish responsibility and that any charge needs a separate review. They state no amount, so the amount is a code rule, as the thresholds are (ADR 0002).

**The fee.** The driver is the Claimant and the claimed fee is a Evidence Item (`EV-DAMAGE-1`, from the trip record). The fee the rider pays is `min(claimed, cap)` with a cap of SGD 50.00 (`CONFIG.cleaning_fee_cap`, a placeholder), for an upheld claim; half of that, rounded half-up to the cent, for a partly upheld claim; nothing for a rejected one. The model chooses the outcome and names `EV-DAMAGE-1` as the input; code computes the number and a model amount is never trusted. The Remedy is `compensation_to_driver` for upheld and partly upheld, `no_action` for rejected. Charging the fee is recommended, never executed.

**Photos.** Each photo gives a capture-time check (by code), a description and an AI-generation signal (by the model), each with its uncertainty (ticket 14). A check is failed or unknown when the capture time is outside the Trip window or missing, the AI-generation signal is anything but `none`, or the photo could not be analysed. Any failed or unknown check caps Confidence at 0.5 (`authenticity_failed_or_unknown`), adds the `authenticity_check` Review Trigger, and so sends the Case to a person. It never decides a Case: a Ruling whose only cited evidence is a failed or unknown photo check is sent back, and it is held if the Judge cannot cite anything else.

**No photos, or analysis off.** The Judge still rules. The material-evidence checklist has a photo line, so Confidence is lower, but nothing is capped.

**Not decided here.** The cap and the half-fee split are placeholders until Ryde supplies a real tariff. What counts as damage that justifies the fee is left to the Judge's reading of the chat and the photo findings.
