"""The demo gate excludes log data until server validation; sessions never call agents."""

from html import escape
import re

import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.api.chat import COOKIE_NAME, SESSION_SECONDS, actor, log_html, route
from src.api.demo import ReplayModel
from src.contracts import LogEventKind
from src.intake import load_catalog
from src.store import CaseStore
from tests import builders as b


def stable_page(text):
    # Session countdown changes on reads; recorded case content must not.
    return re.sub(r"setTimeout\(redactChat,\d+\)", "session-countdown", text)


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("RYDE_CHAT_ACCESS_CODE", "482731")
    store = CaseStore()
    model = ReplayModel(store)
    app = create_app(store=store, model=model, catalog=load_catalog())
    return app, TestClient(app), store, model


def unlock(client, case_id="CASE-0001", code="482731", **kwargs):
    return client.post(f"/cases/{case_id}/chat/unlock", data={"code": code}, follow_redirects=True, **kwargs)


def assert_locked(page):
    assert "Locked" in page.text
    assert "<label for='chat-code'>" in page.text
    assert "type='password'" in page.text
    assert "<ol class='chat-messages'" not in page.text
    assert "<select id='chat-actor'" not in page.text
    assert page.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("code", ["", "wrong", "482731 ", " 482731"])
def test_initial_and_incorrect_responses_contain_no_log_data(setup, code):
    _, client, store, _ = setup
    case = store.create_case(b.a_dispute())
    store.log_event(case.case_id, "evidence", LogEventKind.EVIDENCE_RETURNED,
                    "UNIQUE LOG SUMMARY <script>alert(1)</script>", ["UNIQUE-LOG-REFERENCE"])
    initial = client.get(f"/cases/{case.case_id}")
    denied = unlock(client, case.case_id, code)
    assert initial.status_code == 200
    assert denied.status_code == 403
    for page in [initial, denied]:
        assert_locked(page)
        assert "UNIQUE LOG SUMMARY" not in page.text
        assert "UNIQUE-LOG-REFERENCE" not in page.text
    assert "role='alert'>Incorrect access code" in denied.text
    assert "aria-invalid=true" in denied.text
    assert "value='482731'" not in denied.text


def test_unlock_renders_only_stored_events_in_order_with_citations_and_safe_text(setup):
    _, client, store, model = setup
    client.post("/disputes/DISP-002/run")
    store.log_event("CASE-0001", "new <actor>", LogEventKind.EVIDENCE_RETURNED,
                    "<img src=x onerror=alert(1)>", ["<script>reference</script>"])
    calls = len(model.calls)
    page = unlock(client)
    assert page.status_code == 200
    assert page.headers["cache-control"] == "no-store"
    assert "Rider Advocate" in page.text and "Driver Advocate" in page.text
    assert "Evidence tools" in page.text and "Policy tools" in page.text
    assert "Request → evidence tools" in page.text
    assert "Judge activity → Case store" in page.text
    assert "Case store → Rider notification" in page.text and "Case store → Driver notification" in page.text
    assert "Recorded activity (new &lt;actor&gt;)" in page.text
    positions = []
    cursor = 0
    for event in store.log("CASE-0001"):
        position = page.text.index("<p class='chat-summary'>" + escape(event.summary), cursor)
        positions.append(position)
        cursor = position + 1
    assert positions == sorted(positions)
    for event in store.log("CASE-0001"):
        assert escape(event.timestamp.isoformat()) in page.text
        assert event.kind.value in page.text
        for reference in event.references:
            assert escape(reference) in page.text
    assert "&lt;img src=x onerror=alert(1)&gt;" in page.text
    assert "&lt;script&gt;reference&lt;/script&gt;" in page.text
    assert "<img" not in page.text
    assert "<script>reference" not in page.text
    assert "<option value='Judge'>Judge</option>" in page.text
    assert "<option value='judge_self_check'>" not in page.text
    assert "row.dataset.actor !== this.value" in page.text
    for _ in range(2):
        assert stable_page(client.get("/cases/CASE-0001").text) == stable_page(page.text)
    assert len(model.calls) == calls


def test_cookie_is_opaque_httponly_samesite_and_has_no_code_or_url_secret(setup):
    _, client, store, _ = setup
    store.create_case(b.a_dispute())
    response = client.post("/cases/CASE-0001/chat/unlock", data={"code": "482731"}, follow_redirects=False)
    assert response.status_code == 303
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert f"Max-Age={SESSION_SECONDS}" in cookie
    token = client.cookies.get(COOKIE_NAME)
    assert len(token) >= 32
    assert "482731" not in cookie and "482731" not in response.headers["location"]
    assert response.headers["location"] == "/cases/CASE-0001"
    assert response.headers["cache-control"] == "no-store"


def test_sessions_are_separate_between_clients_and_scoped_to_unlocked_cases(setup):
    app, client, store, _ = setup
    store.create_case(b.a_dispute())
    store.create_case(b.a_dispute())
    assert "<ol class='chat-messages'" in unlock(client).text
    other = TestClient(app)
    assert_locked(other.get("/cases/CASE-0001"))
    assert_locked(client.get("/cases/CASE-0002"))
    assert "<ol class='chat-messages'" in unlock(client, "CASE-0002").text
    assert "<ol class='chat-messages'" in client.get("/cases/CASE-0001").text
    assert_locked(other.get("/cases/CASE-0002"))


def test_lock_revokes_the_server_session_even_if_old_cookie_is_replayed(setup):
    app, client, store, model = setup
    store.create_case(b.a_dispute())
    unlock(client)
    token = client.cookies.get(COOKIE_NAME)
    replay = TestClient(app)
    replay.cookies.set(COOKIE_NAME, token)
    assert "<ol class='chat-messages'" in replay.get("/cases/CASE-0001").text
    response = client.post("/cases/CASE-0001/chat/lock", follow_redirects=True)
    assert_locked(response)
    assert client.cookies.get(COOKIE_NAME) is None
    assert_locked(client.get("/cases/CASE-0001"))
    assert_locked(replay.get("/cases/CASE-0001"))
    assert model.calls == []


def test_expired_session_remains_locked_until_explicit_reentry(setup):
    app, client, store, _ = setup
    now = [100.0]
    app.state.chat_access.clock = lambda: now[0]
    store.create_case(b.a_dispute())
    unlock(client)
    now[0] += SESSION_SECONDS - 1
    assert "<ol class='chat-messages'" in client.get("/cases/CASE-0001").text
    now[0] += 1
    assert_locked(client.get("/cases/CASE-0001"))
    assert_locked(client.get("/cases/CASE-0001"))
    assert "<ol class='chat-messages'" in unlock(client).text


@pytest.mark.parametrize("configured,attempt,success", [("custom-demo", "482731", False), ("custom-demo", "custom-demo", True), ("", "", False), ("", "482731", False)])
def test_configured_code_and_explicit_empty_configuration(monkeypatch, configured, attempt, success):
    monkeypatch.setenv("RYDE_CHAT_ACCESS_CODE", configured)
    store = CaseStore()
    store.create_case(b.a_dispute())
    client = TestClient(create_app(store=store, model=ReplayModel(store), catalog=load_catalog()))
    page = unlock(client, code=attempt)
    assert (page.status_code == 200) is success
    if not success:
        assert_locked(page)


@pytest.mark.parametrize("suffix", ["", "/chat/unlock", "/chat/lock"])
def test_missing_cases_preserve_404_without_creating_sessions(setup, suffix):
    _, client, _, model = setup
    response = client.post(f"/cases/NO-CASE{suffix}", data={"code": "482731"}) if suffix else client.get("/cases/NO-CASE")
    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"
    assert client.cookies.get(COOKIE_NAME) is None
    assert model.calls == []


@pytest.mark.parametrize("category", ["route_deviation", "property_damage"])
def test_rejected_cases_only_show_their_actual_application_events(setup, category):
    _, client, store, _ = setup
    case = store.create_case(b.a_dispute(category=category))
    store.reject_case(case.case_id, "Unsupported category")
    page = unlock(client)
    assert "data-actor='Application'" in page.text
    assert "<option value='Rider Advocate'>" not in page.text
    assert "<option value='Judge'>" not in page.text
    assert "No Ruling" in page.text
    for event in store.log(case.case_id):
        assert escape(event.summary) in page.text


def test_review_case_does_not_acquire_a_final_decision_when_unlocked(setup):
    _, client, store, model = setup
    client.post("/disputes/DISP-004/run")
    calls = len(model.calls)
    page = unlock(client)
    assert "Proposal — no final decision" in page.text
    assert "Case status: pending_review" in page.text
    assert "No payment is authorized or executed" in page.text
    assert "Outcome:" not in page.text and "Amount:" not in page.text
    assert "Rider Advocate" in page.text and "Driver Advocate" in page.text
    assert store.get_case("CASE-0001").ruling.status == "proposal"
    assert len(model.calls) == calls


def test_self_check_is_judge_activity_and_unmatched_outcomes_use_generic_context(setup):
    _, _, store, _ = setup
    case = store.create_case(b.a_dispute())
    store.log_event(case.case_id, "judge_self_check", LogEventKind.SELF_CHECK_FAILED, "Recorded self-check")
    store.log_event(case.case_id, "orchestrator", LogEventKind.OUTCOME_SENT, "Recorded notification without saved Outcome")
    log = store.log(case.case_id)
    assert actor(log[1]) == "Judge"
    assert route(log[1]) == "Judge activity → Case store"
    html = log_html(log, case)
    assert "Case store → party notification" in html
    assert "Case store → Rider notification" not in html
    assert "Case store → Driver notification" not in html


def test_query_code_does_not_unlock_and_duplicate_or_oversized_form_codes_fail_closed(setup):
    _, client, store, _ = setup
    store.create_case(b.a_dispute())
    assert_locked(client.get("/cases/CASE-0001?code=482731"))
    for body in ["code=482731&code=482731", "code=" + "x" * 1025]:
        response = client.post("/cases/CASE-0001/chat/unlock", content=body)
        assert response.status_code == 403
        assert_locked(response)


def test_case_expiry_and_restoration_redact_only_the_log_without_losing_public_case_content(setup):
    _, client, store, _ = setup
    store.create_case(b.a_dispute())
    page = unlock(client)
    assert "function redactChat()" in page.text
    assert "chat.replaceChildren()" in page.text
    assert "addEventListener('pagehide',redactChat)" in page.text
    assert "if(event.persisted)redactChat()" in page.text
    assert "setTimeout(redactChat," in page.text
    assert "retry.textContent='Reload access'" in page.text
    assert "location.reload()" not in page.text


def test_generated_case_script_executes_deadline_and_cross_tab_redaction_preserving_public_content(setup):
    import json
    import shutil
    import subprocess
    _, client, _, _ = setup
    client.post("/disputes/DISP-002/run")
    page = unlock(client).text
    script = re.findall(r"<script>(.*?)</script>", page, re.S)[-1]
    public = page.split("<section class='agent-chat'", 1)[0]
    assert "Ruling" in public and "Policy" in public
    runner = r"""
const vm=require('node:vm'),assert=require('node:assert/strict'),fs=require('node:fs');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
function harness(){
 const listeners={},form={addEventListener:(name,fn)=>{listeners['form:'+name]=fn;}};
 const chat={children:['PRIVATE TRANSCRIPT'],replaceChildren(){this.children=[];},append(...nodes){this.children.push(...nodes);}};
 const publicCase={content:input.public};let expire,delay,invalidation,broadcasts=0;
 const document={getElementById:()=>({addEventListener(){}}),querySelector:selector=>selector==='.agent-chat'?chat:form,querySelectorAll:()=>[],addEventListener:(name,fn)=>{listeners[name]=fn;},createElement:()=>({})};
 const AgentChat={onInvalidation:fn=>{invalidation=fn;},broadcastInvalidation:()=>broadcasts++};
 const window={addEventListener:(name,fn)=>{listeners[name]=fn;}};
 vm.runInNewContext(input.script,{document,window,AgentChat,location:{pathname:'/cases/CASE-0001'},setTimeout:(fn,ms)=>{expire=fn;delay=ms;}});
 return {chat,publicCase,expire,delay,invalidate:()=>invalidation(),listeners,get broadcasts(){return broadcasts;}};
}
for(const trigger of ['deadline','cross-tab','lock','focus','restore']){
 const h=harness();assert(h.delay>0&&h.delay<=1800000);
 if(trigger==='deadline')h.expire();else if(trigger==='cross-tab')h.invalidate();else if(trigger==='lock')h.listeners['form:submit']();else if(trigger==='focus')h.listeners.focus();else h.listeners.pageshow({persisted:true});
 if(trigger==='lock'){assert.equal(h.broadcasts,1);assert.deepEqual(h.chat.children,['PRIVATE TRANSCRIPT']);assert.equal(h.publicCase.content,input.public);continue;}
 assert.equal(h.chat.children.length,2);assert(h.chat.children[0].textContent.startsWith('Locked'));
 assert.equal(h.chat.children[1].href,'/cases/CASE-0001');assert.equal(h.publicCase.content,input.public);
 assert(!JSON.stringify(h.chat).includes('PRIVATE TRANSCRIPT'));
}
"""
    result = subprocess.run([shutil.which("node"), "-e", runner], input=json.dumps({"script": script, "public": public}),
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
