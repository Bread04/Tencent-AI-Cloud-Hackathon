"""Bounded metadata-only report validation, without interpreting party text."""

from math import isfinite

MAX_REQUEST_BYTES = 128 * 1024
MAX_DEPTH = 8


def validate_json(value, depth=0):
    if depth > MAX_DEPTH:
        raise ValueError("Report JSON is too deeply nested.")
    if isinstance(value, dict):
        if len(value) > 128 or any(not isinstance(key, str) or len(key) > 128 for key in value):
            raise ValueError("Invalid report object.")
        for key, item in value.items():
            key.encode("utf-8")
            validate_json(item, depth + 1)
    elif isinstance(value, list):
        if len(value) > 100:
            raise ValueError("Report array is too large.")
        for item in value:
            validate_json(item, depth + 1)
    elif isinstance(value, str):
        value.encode("utf-8")
        if len(value) > 16000:
            raise ValueError("Report text is too long.")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            finite = isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("Report numbers must be finite.")
    elif value is not None and not isinstance(value, bool):
        raise ValueError("Report contains an unsupported JSON value.")


def _object(value, name, allowed):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(f"Invalid {name} metadata.")
    return value


def _strings(value, name, keys, nullable=()):
    for key in keys:
        if key in value and not isinstance(value[key], str) and not (key in nullable and value[key] is None):
            raise ValueError(f"Invalid {name} {key}.")


def validate_report(report, *, confirmed=True, evidence=False):
    validate_json(report)
    _object(report, "report", ("id", "createdAt", "demo", "submitted", "refundProcessed", "mediaIncluded", "reporterRole", "trip", "category", "summary", "statement", "incident", "categoryDetails", "requestedResolution", "evidence", "confirmation"))
    _strings(report, "report", ("id", "createdAt", "reporterRole", "category", "summary", "statement", "confirmation"))
    if report.get("reporterRole") != "Rider":
        raise ValueError("A Rider report is required.")
    if "id" in report and len(report["id"]) > 128:
        raise ValueError("Report ID is too long.")
    if confirmed:
        if report.get("demo") is not True or not isinstance(report.get("confirmation"), str) or not report["confirmation"].strip():
            raise ValueError("Create and confirm a demo Rider report before preparing a case.")
        for key in ("id", "createdAt", "category", "summary", "statement"):
            if not isinstance(report.get(key), str) or not report[key].strip():
                raise ValueError(f"The report needs a valid {key}.")
    for key in ("demo", "submitted", "refundProcessed", "mediaIncluded"):
        if key in report and not isinstance(report[key], bool):
            raise ValueError(f"Invalid report {key}.")
    trip = _object(report.get("trip", {}), "trip", ("reference", "date", "details", "simulatedSourceTrip"))
    _strings(trip, "trip", ("reference", "date", "details"))
    if confirmed or evidence:
        if not isinstance(trip.get("reference"), str) or not trip["reference"].strip() or len(trip["reference"]) > 128:
            raise ValueError("Select a known demo trip before preparing a Rider case.")
    if "simulatedSourceTrip" in trip and not isinstance(trip["simulatedSourceTrip"], bool):
        raise ValueError("Invalid trip source flag.")
    details = report.get("categoryDetails", {})
    if not isinstance(details, dict) or any(not isinstance(value, str) for value in details.values()):
        raise ValueError("Report category details are invalid.")
    incident = _object(report.get("incident", {}), "incident", ("time", "timeUnknown", "timeZone", "location"))
    _strings(incident, "incident", ("time", "timeZone", "location"), nullable=("time",))
    if "timeUnknown" in incident and not isinstance(incident["timeUnknown"], bool):
        raise ValueError("Invalid incident time flag.")
    request = _object(report.get("requestedResolution", {}), "requested resolution", ("type", "amount", "currency", "details"))
    _strings(request, "requested resolution", ("type", "currency", "details"))
    if "amount" in request and (isinstance(request["amount"], bool) or not isinstance(request["amount"], (int, float)) or request["amount"] <= 0 or request.get("currency") != "SGD"):
        raise ValueError("A requested amount must be positive and use SGD.")
    attachments = report.get("evidence", [])
    if not isinstance(attachments, list) or len(attachments) > 20 or (confirmed and "evidence" not in report):
        raise ValueError("Report attachment metadata is invalid.")
    for item in attachments:
        _object(item, "attachment", ("originalFilename", "type", "sizeBytes", "source", "lastModified", "lastModifiedNote", "caption", "takenAtUserReported", "takenAtTimeZone"))
        _strings(item, "attachment", ("originalFilename", "type", "source", "lastModified", "lastModifiedNote", "caption", "takenAtUserReported", "takenAtTimeZone"), nullable=("lastModified", "takenAtUserReported"))
        if "sizeBytes" in item and (isinstance(item["sizeBytes"], bool) or not isinstance(item["sizeBytes"], int) or not 0 <= item["sizeBytes"] <= 100 * 1024 * 1024):
            raise ValueError("Invalid attachment size.")


def validate_scope(rider_id, trip_id):
    if not isinstance(rider_id, str) or not rider_id.strip() or len(rider_id) > 128:
        raise ValueError("Select a valid simulated Rider.")
    if not isinstance(trip_id, str) or not trip_id.strip() or len(trip_id) > 128:
        raise ValueError("Select a valid simulated Trip.")
