"""Public log presentation and an app-local demo access gate; no agent calls."""

from collections.abc import Callable
from copy import deepcopy
from html import escape
import json
import secrets
from threading import Lock
import time
from urllib.parse import quote

from src.contracts import Case, LogEvent

COOKIE_NAME = "ryde_chat_session"
SESSION_SECONDS = 30 * 60
CLIENT_COOKIE_NAME = "ryde_chat_client"
TRANSCRIPT_SECONDS = 6 * 60 * 60
MAX_TRANSCRIPT_BYTES = 256 * 1024


class RiderTranscripts:
    """Bounded app-local public activity storage; server workflows or legacy migration."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, *, max_records=1000,
                 max_bytes=16 * 1024 * 1024):
        self.clock = clock
        self.max_records = max_records
        self.max_bytes = max_bytes
        self._records = {}
        self._lock = Lock()

    def _prune(self):
        now = self.clock()
        self._records = {key: value for key, value in self._records.items() if value[0] > now}

    def register(self, payload: dict, previous_owner: str | None) -> tuple[str, str]:
        size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        with self._lock:
            self._prune()
            if len(self._records) >= self.max_records or sum(row[3] for row in self._records.values()) + size > self.max_bytes:
                raise OverflowError("Communication Log storage is full. Retry later or restart the local demo.")
            owner = previous_owner if previous_owner and any(row[1] == previous_owner for row in self._records.values()) else secrets.token_urlsafe(32)
            handle = secrets.token_urlsafe(32)
            self._records[handle] = (self.clock() + TRANSCRIPT_SECONDS, owner, deepcopy(payload), size)
            return handle, owner

    def get(self, handle: str, owner: str | None, *, metadata_only=False) -> dict:
        with self._lock:
            self._prune()
            entry = self._records.get(handle)
            if entry is None:
                raise KeyError(handle)
            if not owner or not owner.isascii() or not secrets.compare_digest(owner, entry[1]):
                raise PermissionError("This Communication Log belongs to a different browser session.")
            return {} if metadata_only else deepcopy(entry[2])

    def remaining(self, handle: str) -> float:
        with self._lock:
            entry = self._records.get(handle)
            return max(0, entry[0] - self.clock()) if entry else 0


def validate_rider_transcript(payload) -> bool:
    """Allow only the recorded public log and three minimal scope identifiers."""
    if not isinstance(payload, dict) or set(payload) != {"context", "communication_log"}:
        return False
    context, log = payload["context"], payload["communication_log"]
    if not isinstance(context, dict) or set(context) != {"rider_id", "trip_id", "report_id"}:
        return False
    if any(not isinstance(value, str) or not value or len(value) > 128 for value in context.values()):
        return False
    if not isinstance(log, list) or len(log) > 512:
        return False
    for event in log:
        if not isinstance(event, dict) or set(event) - {"agent", "kind", "summary", "timestamp", "references"}:
            return False
        for name, limit in [("agent", 256), ("kind", 128), ("summary", 8192)]:
            if not isinstance(event.get(name), str) or len(event[name]) > limit:
                return False
        if "timestamp" in event and (not isinstance(event["timestamp"], str) or len(event["timestamp"]) > 128):
            return False
        refs = event.get("references", [])
        if not isinstance(refs, list) or len(refs) > 128 or any(not isinstance(ref, str) or len(ref) > 256 for ref in refs):
            return False
    try:
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


class ChatAccess:
    """Opaque, expiring sessions, scoped to explicitly unlocked Cases."""

    def __init__(self, code: str, clock: Callable[[], float] = time.monotonic):
        self._code = code
        self.clock = clock
        self._sessions: dict[str, tuple[float, frozenset[str]]] = {}
        self._lock = Lock()

    def _prune(self) -> None:
        now = self.clock()
        self._sessions = {token: entry for token, entry in self._sessions.items() if entry[0] > now}

    def allowed(self, token: str | None, case_id: str) -> bool:
        with self._lock:
            self._prune()
            entry = self._sessions.get(token)
            return entry is not None and case_id in entry[1]

    def remaining(self, token: str | None) -> float:
        with self._lock:
            entry = self._sessions.get(token)
            return max(0, entry[0] - self.clock()) if entry else 0

    def unlock(self, code: str, case_id: str, previous: str | None) -> str | None:
        with self._lock:
            self._prune()
            existing = self._sessions.get(previous)
            try:
                valid = bool(self._code) and secrets.compare_digest(code.encode("utf-8"), self._code.encode("utf-8"))
            except UnicodeEncodeError:
                valid = False
            if not valid:
                self._sessions.pop(previous, None)
                return None
            cases = existing[1] if existing else frozenset()
            # Preserve the opaque token so concurrent valid requests atomically union scopes.
            token = previous if existing else secrets.token_urlsafe(32)
            self._sessions[token] = (self.clock() + SESSION_SECONDS, cases | {case_id})
            return token

    def revoke(self, token: str | None) -> None:
        with self._lock:
            self._sessions.pop(token, None)


def case_path(case_id: str) -> str:
    return "/cases/" + quote(case_id, safe="")


def locked_html(case_id: str, error: str = "", *, focus=False) -> str:
    return (
        "<section class='agent-chat' aria-label='Communication Log'>"
        "<header><p>Recorded collaboration</p><h2>Communication Log</h2></header>"
        "<p class='chat-note'>The Case store coordinates handoffs. Advocates do not chat directly with each other. "
        "Evidence and policy functions are code tools, not additional model agents.</p>"
        "<p class='chat-note'><strong>Locked</strong> · Enter the demo access code to view recorded activity.</p>"
        f"<form class='chat-gate' method='post' action='{case_path(case_id)}/chat/unlock'>"
        "<label for='chat-code'>Communication Log access code</label>"
        "<input id='chat-code' name='code' type='password' inputmode='numeric' autocomplete='off' "
        f"aria-describedby='chat-error'{' aria-invalid=true' if error else ''}>"
        "<button type='submit'>Unlock</button>"
        f"<p id='chat-error' role='alert'>{escape(error)}</p></form></section>"
        "<script src='/shared/agent-chat.js?feature=agent-chat-v3'></script>"
        + ("<script>AgentChat.invalidate();</script>" if error else "")
        + ("<script>document.getElementById('chat-code').focus();</script>" if error or focus else "")
    )


def actor(event: LogEvent) -> str:
    if event.kind.value in ("self_check_passed", "self_check_failed") or event.agent == "judge_self_check":
        return "Judge"
    return {
        "rider_advocate": "Rider Advocate", "driver_advocate": "Driver Advocate", "judge": "Judge",
        "evidence": "Evidence tools", "policy": "Policy tools", "orchestrator": "Application",
        "intake": "Application", "escalation": "Application",
    }.get(event.agent, f"Recorded activity ({event.agent})")


def route(event: LogEvent, recipient: str = "") -> str:
    kind = event.kind.value
    if kind == "evidence_requested":
        return "Request → evidence tools"
    if kind == "outcome_sent":
        return f"Case store → {recipient.capitalize()} notification" if recipient else "Case store → party notification"
    if kind == "escalated":
        return "Case store → Human review routing context"
    if kind in ("evidence_returned", "policy_retrieved", "precedent_retrieved", "submission_filed", "ruling_drafted"):
        return "Recorded return → Case store"
    if kind in ("self_check_passed", "self_check_failed", "argument_assessed", "stability_check"):
        return "Judge activity → Case store"
    return "Recorded coordination · Case store"


def log_html(log: list[LogEvent], case: Case, remaining: float = SESSION_SECONDS) -> str:
    actors = list(dict.fromkeys(actor(event) for event in log))
    options = "".join(f"<option value='{escape(name, quote=True)}'>{escape(name)}</option>" for name in actors)
    outcome_count = sum(event.kind.value == "outcome_sent" for event in log)
    outcome_index = 0
    rows = []
    for event in log:
        recipient = ""
        if event.kind.value == "outcome_sent":
            if outcome_count == len(case.outcomes):
                recipient = case.outcomes[outcome_index].party.value
            outcome_index += 1
        sender = actor(event)
        timestamp = event.timestamp.isoformat()
        references = ""
        if event.references:
            references = "<p class='chat-citations'>" + " · ".join(escape(ref) for ref in event.references) + "</p>"
        rows.append(
            f"<li class='chat-message' data-actor='{escape(sender, quote=True)}'>"
            f"<div class='chat-meta'><strong>{escape(sender)}</strong><span>{escape(event.agent)} · {escape(event.kind.value)}</span></div>"
            f"<p class='chat-route'>{escape(route(event, recipient))}</p>"
            f"<time datetime='{escape(timestamp, quote=True)}'>{escape(timestamp)}</time>"
            f"<p class='chat-summary'>{escape(event.summary)}</p>{references}</li>"
        )
    transcript = "".join(rows) or "<li>No recorded activity.</li>"
    return (
        "<section class='agent-chat' aria-label='Communication Log'>"
        "<header><div><p>Recorded collaboration</p><h2>Communication Log</h2></div>"
        f"<form method='post' action='{case_path(case.case_id)}/chat/lock'><button>Lock</button></form></header>"
        "<p class='chat-note'>The Case store coordinates handoffs. Advocates do not chat directly with each other. "
        "Evidence and policy functions are code tools, not additional model agents. Only stored public summaries are shown.</p>"
        f"<p class='chat-note'>Case status: {escape(case.status.value)}</p>"
        "<div class='chat-filter'><label for='chat-actor'>Filter activity by actor</label>"
        f"<select id='chat-actor'><option value=''>All activity</option>{options}</select></div>"
        f"<ol class='chat-messages' aria-live='polite'>{transcript}</ol></section>"
        "<script src='/shared/agent-chat.js?feature=agent-chat-v3'></script>"
        "<script>document.getElementById('chat-actor').addEventListener('change', function () {"
        "document.querySelectorAll('.chat-message').forEach(row => {row.hidden = !!this.value && row.dataset.actor !== this.value;});"
        "});function redactChat(){const chat=document.querySelector('.agent-chat');chat.replaceChildren();"
        "const message=document.createElement('p');message.textContent='Locked · Reload access to recheck your Communication Log session.';"
        "const retry=document.createElement('a');retry.href=location.pathname;retry.textContent='Reload access';chat.append(message,retry);}"
        "window.addEventListener('pagehide',redactChat);"
        "window.addEventListener('pageshow',event=>{if(event.persisted)redactChat();});"
        "AgentChat.onInvalidation(redactChat);"
        "document.querySelector('.agent-chat form').addEventListener('submit',()=>AgentChat.broadcastInvalidation());"
        "window.addEventListener('focus',redactChat);"
        "document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')redactChat();});"
        f"setTimeout(redactChat,{int(remaining * 1000)});</script>"
    )


CHAT_STYLE = """
.agent-chat{font-family:system-ui,sans-serif;max-width:900px;margin:28px 0;border:1px solid #ccd7ec;background:#f5f7fc;color:#17202d;overflow-wrap:anywhere}
.agent-chat header{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;padding:22px;background:#17202d;color:#fff}
.agent-chat header p{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#b9cbff;margin:0 0 8px}.agent-chat h2{margin:0;font-size:22px}
.agent-chat .chat-note{font-size:13px;line-height:1.7;margin:18px 22px;color:#526176}
.agent-chat .chat-gate{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;padding:0 22px 22px}
.agent-chat label{font-size:13px;font-weight:600}.agent-chat .chat-gate label,.agent-chat #chat-error{grid-column:1/-1}
.agent-chat input,.agent-chat select{box-sizing:border-box;min-width:0;min-height:44px;border:1px solid #a8b7d0;padding:10px;background:#fff;color:#17202d;font:inherit}
.agent-chat button{min-height:44px;border:1px solid #315cf5;background:#315cf5;color:#fff;padding:10px 18px;font:inherit;font-size:13px;cursor:pointer}
.agent-chat header button{background:transparent;border-color:#8fa5d9}.agent-chat form{margin:0}.agent-chat #chat-error{color:#a32036;font-size:13px;margin:0}
.agent-chat :is(button,input,select):focus-visible{outline:3px solid #7195ff;outline-offset:3px}
.agent-chat .chat-filter{display:flex;align-items:center;gap:16px;padding:16px 22px;border-bottom:1px solid #dce3f0}
.agent-chat .chat-messages{list-style:none;display:grid;gap:14px;max-height:620px;overflow-y:auto;margin:0;padding:20px 22px}
.agent-chat .chat-message{background:#fff;border:1px solid #d9e2f0;border-left:3px solid #315cf5;padding:16px;min-width:0}
.agent-chat .chat-message[hidden]{display:none}.agent-chat .chat-meta{display:flex;justify-content:space-between;gap:12px;align-items:baseline;font-size:14px}
.agent-chat .chat-meta span,.agent-chat time{font-size:11px;color:#64718a}.agent-chat .chat-route{font-size:12px;color:#2548a4;margin:9px 0 5px}
.agent-chat .chat-summary{font-size:14px;line-height:1.7;white-space:pre-wrap;margin:12px 0 0}
.agent-chat .chat-citations{font-size:11px;line-height:1.8;color:#4e617f;border-top:1px solid #e4eaf4;padding-top:10px;margin:12px 0 0}
@media(max-width:600px){.agent-chat header{padding:17px 14px}.agent-chat .chat-note{margin:14px}.agent-chat .chat-gate{padding:0 14px 16px}.agent-chat .chat-filter{padding:14px;display:grid;gap:8px}.agent-chat .chat-messages{padding:14px}.agent-chat .chat-message{padding:13px}.agent-chat .chat-meta{display:grid;gap:5px}}
"""
