"""Bounded same-origin local Rider APIs. Rider selection is simulated identity."""

from copy import deepcopy
import json

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from src.agents import rider
from src.agents.rider import evidence, policy
from src.agents.rider.validation import MAX_REQUEST_BYTES, validate_json, validate_scope
from src.api.chat import CLIENT_COOKIE_NAME, TRANSCRIPT_SECONDS


async def read_payload(request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_REQUEST_BYTES:
            raise ValueError("Rider request is too large.")
    try:
        # Reject duplicate keys, NaN/Infinity, invalid UTF-8 and excessive depth.
        def pairs(entries):
            result = {}
            for key, value in entries:
                if key in result:
                    raise ValueError("Duplicate JSON field.")
                result[key] = value
            return result
        def constant(_):
            raise ValueError("Non-finite JSON value.")
        payload = json.loads(body.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
        validate_json(payload)
        if not isinstance(payload, dict):
            raise ValueError("A Rider request object is required.")
        return payload
    except (UnicodeError, RecursionError, OverflowError) as error:
        raise ValueError("Invalid Rider JSON metadata.") from error


def install_rider_routes(app, transcripts):
    def response_with_log(result, context, log, request):
        handle, owner = transcripts.register({"context": context, "communication_log": log}, request.cookies.get(CLIENT_COOKIE_NAME))
        redacted = deepcopy(result)
        if "communication_log" in redacted:
            redacted["communication_log"] = []
        if "log" in redacted:
            redacted["log"] = []
        if "evidence" in redacted:
            redacted["evidence"]["log"] = []
        redacted["transcript_handle"] = handle
        response = JSONResponse(redacted)
        response.set_cookie(CLIENT_COOKIE_NAME, owner, httponly=True, samesite="strict", max_age=TRANSCRIPT_SECONDS, secure=request.url.scheme == "https")
        return response

    async def execute(request, action):
        try:
            payload = await read_payload(request)
            return await action(payload)
        except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError) as error:
            # Validation errors describe the field; never echo party text or telemetry.
            if isinstance(error, OverflowError):
                return JSONResponse({"error": "Communication Log storage is full. Retry later or restart the local demo."}, status_code=503)
            return JSONResponse({"error": str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else "Invalid Rider request metadata."}, status_code=400)

    @app.post("/api/rider/cases")
    async def prepare_case(request: Request):
        async def action(payload):
            if set(payload) != {"riderId", "report"}:
                raise ValueError("A Rider case request needs only riderId and report.")
            trip_id = payload["report"].get("trip", {}).get("reference") if isinstance(payload["report"], dict) and isinstance(payload["report"].get("trip"), dict) else None
            validate_scope(payload["riderId"], trip_id)
            result = await run_in_threadpool(rider.run, report=payload["report"], rider_id=payload["riderId"])
            return response_with_log(result, result["context"], result["communication_log"], request)
        return await execute(request, action)

    @app.post("/api/rider/evidence")
    async def collect_evidence(request: Request):
        async def action(payload):
            if set(payload) - {"riderId", "tripId", "report"} or not {"riderId", "tripId"} <= set(payload):
                raise ValueError("A Rider evidence request needs riderId, tripId and optional report only.")
            result = await run_in_threadpool(evidence.collect, rider_id=payload["riderId"], trip_id=payload["tripId"], report=payload.get("report"))
            report_id = (payload.get("report") or {}).get("id") or "standalone-evidence"
            context = {"rider_id": result["rider_id"], "trip_id": result["trip_id"], "report_id": report_id}
            return response_with_log({**result, "context": context}, context, result["log"], request)
        return await execute(request, action)

    @app.post("/api/rider/policy-preview")
    async def preview_policy(request: Request):
        async def action(payload):
            if set(payload) != {"report"}:
                raise ValueError("A policy preview request needs only report metadata.")
            return JSONResponse(await run_in_threadpool(policy.preview, payload["report"]))
        return await execute(request, action)
