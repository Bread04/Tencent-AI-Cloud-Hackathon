"""Turn a report from the rider app's report form into a Dispute (ticket 19).

The form's own words (`category`, `reporterRole`, ...) are mapped here, once, onto the contract. The report
is kept exactly as submitted in `Dispute.filed_report`; everything else on the Dispute is read from it.
A report the workflow cannot take is refused with a reason a person can act on, before any Case exists.
"""

import json
from copy import deepcopy
from datetime import datetime, timezone

from pydantic import ValidationError

from src.contracts import Dispute, DisputeCategory, Incident, Party, RequestedResolution
from src.intake.catalog import Catalog, UnknownTrip

# The form's category choices that the workflow resolves. Safety / conduct is accepted here and routed to a human reviewer by the orchestrator.
CATEGORIES = {
    "No-show / cancellation": DisputeCategory.NO_SHOW_CHARGE,
    "Route deviation": DisputeCategory.ROUTE_DEVIATION,
    "Damage / mess": DisputeCategory.PROPERTY_DAMAGE,
    "Safety / conduct": DisputeCategory.SAFETY_INCIDENT,
}
ROLES = {"Rider": Party.RIDER, "Driver": Party.DRIVER}


class ReportError(ValueError):
    """The report cannot be filed as a Dispute; the message says why, in words for the person who filed it."""


def dispute_from_report(report: dict, catalog: Catalog, *, now: datetime | None = None) -> Dispute:
    if not isinstance(report, dict):
        raise ReportError("A report object is required.")
    report_id = _text(report.get("id"))
    if not report_id:
        raise ReportError("The report needs a report ID.")
    role = ROLES.get(report.get("reporterRole"))
    if role is None:
        raise ReportError("The report must be filed as a Rider or Driver.")
    trip = report.get("trip")
    trip_id = _text(trip.get("reference")) if isinstance(trip, dict) else ""
    if not trip_id:
        raise ReportError("The report needs a trip reference.")
    try:
        catalog.trip(trip_id)
    except UnknownTrip:
        raise ReportError(f"Trip {trip_id} does not exist.") from None
    category_name = report.get("category")
    category = CATEGORIES.get(category_name) if isinstance(category_name, str) else None
    if category is None:
        raise ReportError(f"{category_name or 'This'} disputes cannot be resolved yet; supported: {', '.join(CATEGORIES)}.")
    statement = _text(report.get("statement"))
    if not statement:
        raise ReportError("The report needs a statement of what happened.")

    resolution = _requested_resolution(report.get("requestedResolution"))
    try:
        return Dispute(
            dispute_id=f"DISP-{report_id}",
            trip_id=trip_id,
            filed_by=role,
            category=category,
            description=statement,
            requested_remedy=_remedy_text(resolution),
            filed_at=now or datetime.now(timezone.utc),
            filed_report=json.loads(json.dumps(report)),  # a private copy of the report as submitted
            incident=_incident(report.get("incident")),
            category_details=_category_details(report.get("categoryDetails")),
            requested_resolution=resolution,
        )
    except ValidationError as error:  # not reachable for the fields checked above, but never leak a stack trace
        raise ReportError(f"The report could not be filed: {error.errors()[0]['msg']}") from None


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _incident(value) -> Incident | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ReportError("The incident details must be an object.")
    raw_time = None if value.get("timeUnknown") else value.get("time")
    try:
        when = datetime.fromisoformat(raw_time) if raw_time else None
        return Incident(time=when, time_zone=_text(value.get("timeZone")), location=_text(value.get("location")) or None)
    except (ValueError, TypeError, ValidationError):
        raise ReportError("The incident time and time zone could not be read.") from None


def _category_details(value) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ReportError("The category details must be a set of answers.")
    return {key: str(answer) for key, answer in value.items() if answer not in (None, "")}


def _requested_resolution(value) -> RequestedResolution | None:
    if value is None:
        return None
    try:
        return RequestedResolution(
            type=value.get("type"), amount=value.get("amount"), currency=value.get("currency"), details=_text(value.get("details")) or None
        )
    except (ValidationError, AttributeError):
        raise ReportError("The requested resolution is not valid: give a type, and a positive amount with its currency.") from None


def _remedy_text(resolution: RequestedResolution | None) -> str:
    if resolution is None:
        return "Review the report"
    parts = [resolution.type]
    if resolution.amount is not None:
        parts.append(f"{resolution.currency} {resolution.amount.normalize():f}")
    if resolution.details:
        parts.append(resolution.details)
    return " · ".join(parts)
