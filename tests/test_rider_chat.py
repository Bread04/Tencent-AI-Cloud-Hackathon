"""Same-origin Rider transcript boundary: public uploads, protected reads, no agents."""

from copy import deepcopy

from fastapi.testclient import TestClient
import pytest

from src.api.chat import CLIENT_COOKIE_NAME, COOKIE_NAME, MAX_TRANSCRIPT_BYTES, SESSION_SECONDS, TRANSCRIPT_SECONDS, RiderTranscripts
from tests.test_chat import setup, assert_locked
from tests import builders as b

BASE = "/api/rider-chat/transcripts"


def payload():
    return {"context": {"rider_id": "R-7823", "trip_id": "TRIP-TEST", "report_id": "REPORT-TEST"},
            "communication_log": [
                {"agent": "Application", "kind": "handoff_recorded", "summary": "UNIQUE PUBLIC ACTIVITY",
                 "timestamp": "2026-10-12T00:00:00Z", "references": ["UNIQUE-REFERENCE"]},
                {"agent": "Unknown <actor>", "kind": "recorded", "summary": "<img src=x onerror=alert(1)>"}]}


def register(client, data=None):
    response = client.post(BASE, json=data if data is not None else payload())
    assert response.status_code == 201
    assert "UNIQUE PUBLIC ACTIVITY" not in response.text
    assert "UNIQUE-REFERENCE" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert set(response.json()) == {"handle", "expires_in"}
    assert len(response.json()["handle"]) >= 32
    return BASE + "/" + response.json()["handle"]


@pytest.mark.parametrize("code", ["", "wrong", " 482731", "482731 ", None, 482731])
def test_rider_locked_and_denied_reads_contain_no_activity(setup, code):
    _, client, _, model = setup
    path = register(client)
    for response in [client.get(path), client.post(path + "/unlock", json={"code": code}), client.get(path)]:
        assert response.status_code == 403
        assert "UNIQUE PUBLIC ACTIVITY" not in response.text
        assert "UNIQUE-REFERENCE" not in response.text
        assert "communication_log" not in response.text
        assert response.headers["cache-control"] == "no-store"
    assert model.calls == []


def test_rider_unlock_returns_nothing_until_separate_protected_read_and_preserves_public_events(setup):
    _, client, _, model = setup
    path = register(client)
    cookie = client.cookies.get(CLIENT_COOKIE_NAME)
    assert len(cookie) >= 32 and "482731" not in cookie
    response = client.post(path + "/unlock", json={"code": "482731"})
    assert response.status_code == 204 and not response.content
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=strict" in response.headers["set-cookie"]
    assert "482731" not in response.headers["set-cookie"]
    read = client.get(path)
    assert read.status_code == 200
    assert read.json()["communication_log"] == payload()["communication_log"]
    assert read.json()["context"] == payload()["context"]
    assert 0 < read.json()["expires_in"] <= SESSION_SECONDS
    assert read.headers["cache-control"] == "no-store"
    assert model.calls == []


def test_other_browser_cannot_unlock_known_handle_even_with_valid_code_and_session_cookie(setup):
    app, client, _, _ = setup
    path = register(client)
    client.post(path + "/unlock", json={"code": "482731"})
    other = TestClient(app)
    other.cookies.set(COOKIE_NAME, client.cookies.get(COOKIE_NAME))
    for response in [other.get(path), other.post(path + "/unlock", json={"code": "482731"})]:
        assert response.status_code == 403
        assert "communication_log" not in response.text and "UNIQUE" not in response.text
    other_path = register(other)
    assert other.get(other_path).status_code == 403
    assert client.get(other_path).status_code == 403


def test_handle_scoping_expiry_and_shared_revocation_with_case_pages(setup):
    app, client, store, model = setup
    now = [100.0]
    app.state.chat_access.clock = lambda: now[0]
    first, second = register(client), register(client)
    client.post(first + "/unlock", json={"code": "482731"})
    assert client.get(first).status_code == 200 and client.get(second).status_code == 403
    now[0] += SESSION_SECONDS
    assert client.get(first).status_code == 403
    client.post(first + "/unlock", json={"code": "482731"})
    store.create_case(b.a_dispute())
    client.post("/cases/CASE-0001/chat/unlock", data={"code": "482731"})
    token = client.cookies.get(COOKIE_NAME)
    client.post(second + "/lock")
    assert_locked(client.get("/cases/CASE-0001"))
    replay = TestClient(app)
    replay.cookies.set(COOKIE_NAME, token)
    replay.cookies.set(CLIENT_COOKIE_NAME, client.cookies.get(CLIENT_COOKIE_NAME))
    assert replay.get(first).status_code == 403
    client.post(first + "/unlock", json={"code": "482731"})
    client.post("/cases/CASE-0001/chat/lock")
    assert client.get(first).status_code == 403
    assert model.calls == []


@pytest.mark.parametrize("suffix,method", [("", "get"), ("/unlock", "post"), ("/lock", "post")])
def test_unknown_handles_and_restart_fail_closed_with_reprepare_path(setup, suffix, method):
    _, client, _, model = setup
    path = register(client)
    # A fresh app models restart: old browser content can survive, server records cannot.
    from src.api.demo import create_demo_app
    restarted = TestClient(create_demo_app())
    for target in [BASE + "/unknown", path]:
        response = getattr(restarted, method)(target + suffix)
        assert response.status_code == 404
        assert response.headers["cache-control"] == "no-store"
        assert "prepare" in response.text and "communication_log" not in response.text
    assert model.calls == []


def test_retention_and_repository_capacity_are_bounded_without_mutating_stored_activity(setup):
    app, client, _, _ = setup
    now = [100.0]
    app.state.rider_transcripts.clock = lambda: now[0]
    path = register(client)
    now[0] += TRANSCRIPT_SECONDS
    assert client.get(path).status_code == 404
    repo = RiderTranscripts(clock=lambda: now[0], max_records=1)
    source = payload()
    handle, owner = repo.register(source, None)
    source["communication_log"].clear()
    assert repo.get(handle, owner) == payload()
    with pytest.raises(OverflowError):
        repo.register(payload(), owner)
    assert repo.get(handle, owner, metadata_only=True) == {}
    now[0] += TRANSCRIPT_SECONDS
    assert repo.register(payload(), owner)[0] != handle
    with pytest.raises(OverflowError):
        RiderTranscripts(max_bytes=1).register(payload(), None)


@pytest.mark.parametrize("change", [
    lambda data: data.update(original_report={"statement": "Do not upload me"}),
    lambda data: data["context"].update(media="Do not upload me"),
    lambda data: data["communication_log"][0].update(private_reasoning="Do not upload me"),
    lambda data: data["communication_log"].append({"agent": "A", "kind": "K", "summary": "x" * 8193}),
    lambda data: data.update(communication_log=[data["communication_log"][0]] * 513),
    lambda data: data["communication_log"][0].update(references=[{}]),
])
def test_invalid_uploads_never_echo_activity_or_create_cookie(setup, change):
    _, client, _, _ = setup
    data = deepcopy(payload())
    change(data)
    response = client.post(BASE, json=data)
    assert response.status_code == 400 and "UNIQUE" not in response.text
    assert client.cookies.get(CLIENT_COOKIE_NAME) is None


def test_oversized_and_invalid_json_uploads_are_rejected_without_echo(setup):
    _, client, _, _ = setup
    for body in [b"x" * (MAX_TRANSCRIPT_BYTES + 1), b"{broken", b"\xff"]:
        assert client.post(BASE, content=body).status_code == 400


@pytest.mark.parametrize("configured,code,expected", [("", "482731", 403), ("custom", "482731", 403), ("custom", "custom", 204)])
def test_rider_uses_server_configuration_and_explicit_empty_fails_closed(monkeypatch, configured, code, expected):
    monkeypatch.setenv("RYDE_CHAT_ACCESS_CODE", configured)
    from src.api.demo import create_demo_app
    client = TestClient(create_demo_app())
    path = register(client)
    assert client.post(path + "/unlock", json={"code": code}).status_code == expected


def test_one_backend_preserves_home_and_serves_both_apps_and_assets_without_model_calls(setup):
    _, client, _, model = setup
    assert "Dispute console · Waypoint" in client.get("/").text
    for path in ["/index.html", "/ryde-app/", "/ryde-app/index.html", "/ryde-report/", "/ryde-report/index.html", "/prototypes/ryde-app/index.html", "/prototypes/ryde-report/index.html", "/shared/agent-chat.js?feature=agent-chat-v3", "/static/console.js"]:
        assert client.get(path).status_code == 200
    assert client.get("/api/rider-chat/transcripts/unknown").status_code == 404
    assert client.get("/not-an-asset").status_code == 404
    assert client.get("/src/api/chat.py").status_code == 404
    js = client.get("/shared/agent-chat.js").text
    assert "482731" not in js and "sessionStorage" not in js and "WaypointChatDemoCode" not in js
    assert model.calls == []


def test_read_deadline_includes_remaining_transcript_retention(setup):
    app, client, _, _ = setup
    now = [100.0]
    app.state.rider_transcripts.clock = lambda: now[0]
    app.state.chat_access.clock = lambda: now[0]
    path = register(client)
    now[0] += TRANSCRIPT_SECONDS - 2
    assert client.post(path + "/unlock", json={"code": "482731"}).status_code == 204
    assert client.get(path).json()["expires_in"] == 2
    now[0] += 2
    assert client.get(path).status_code == 404


def test_non_ascii_owner_cookie_is_denied_without_server_error(setup):
    _, client, _, _ = setup
    path = register(client)
    response = client.get(path, headers={"cookie": 'ryde_chat_client="\\351"'})
    assert response.status_code == 403


@pytest.mark.parametrize("field", ["context", "summary", "reference"])
def test_escaped_surrogates_in_upload_are_invalid_utf8(setup, field):
    import json
    _, client, _, _ = setup
    data = payload()
    if field == "context":
        data["context"]["report_id"] = "\ud800"
    elif field == "summary":
        data["communication_log"][0]["summary"] = "\ud800"
    else:
        data["communication_log"][0]["references"] = ["\udfff"]
    response = client.post(BASE, content=json.dumps(data))
    assert response.status_code == 400
    assert client.cookies.get(CLIENT_COOKIE_NAME) is None


def test_surrogate_access_codes_fail_closed_on_both_surfaces(setup):
    import json
    _, client, store, _ = setup
    path = register(client)
    assert client.post(path + "/unlock", content=json.dumps({"code": "\ud800"})).status_code == 403
    store.create_case(b.a_dispute())
    assert client.post("/cases/CASE-0001/chat/unlock", content=b"code=%ED%A0%80").status_code == 403
    assert client.cookies.get(COOKIE_NAME) is None


def test_concurrent_unlock_requests_with_existing_cookie_union_scopes_and_revoke_together(setup):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    app, client, store, _ = setup
    first, second = register(client), register(client)
    store.create_case(b.a_dispute())
    client.post(first + "/unlock", json={"code": "482731"})
    token, owner = client.cookies.get(COOKIE_NAME), client.cookies.get(CLIENT_COOKIE_NAME)
    barrier = Barrier(2)

    def request(path):
        peer = TestClient(app)
        peer.cookies.set(COOKIE_NAME, token, domain="testserver.local")
        peer.cookies.set(CLIENT_COOKIE_NAME, owner, domain="testserver.local")
        barrier.wait()
        response = peer.post(path, json={"code": "482731"}) if path.startswith(BASE) else peer.post(path, data={"code": "482731"}, follow_redirects=False)
        return response.status_code, peer.cookies.get(COOKIE_NAME)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(request, [second + "/unlock", "/cases/CASE-0001/chat/unlock"]))
    assert outcomes == [(204, token), (303, token)]
    assert client.get(first).status_code == client.get(second).status_code == 200
    assert "<ol class='chat-messages'" in client.get("/cases/CASE-0001").text
    client.post(first + "/lock")
    assert not app.state.chat_access.allowed(token, "CASE-0001")
    assert not app.state.chat_access.allowed(token, "rider:" + second.rsplit("/", 1)[1])
