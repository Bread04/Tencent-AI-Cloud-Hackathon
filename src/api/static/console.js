// Demo Day console. Reads the JSON API (or a recorded stream with ?recorded=1) and fills in the rider app's trip panel.
// Everything is built with textContent, never innerHTML, so case text cannot inject markup.
(() => {
  "use strict";

  const params = new URLSearchParams(location.search);
  // The console has no on-page controls. Presenters use the URL: ?recorded=1 replays /static/recorded/<dispute>.json (no model is
  // called), ?pace=<ms> sets the replay speed, and ?<switch>=1 turns on a demo switch (the table is in src/api/demo_switches.py).
  const isRecorded = () => params.has("recorded");
  const POLL_MS = 400;
  const SWITCHES = JSON.parse(document.body.dataset.switches); // [{name, needsPhotos, liveOnly}], from the table
  let photosOnHand = false; // photo analysis only means something for a Dispute that has photos
  let safetyIncident = false; // a Safety Incident is only accepted with SLA routing on (it goes to a person at the front of the queue), so the console turns it on
  const on = new Set(SWITCHES.filter((s) => params.has(s.name)).map((s) => s.name)); // the supporting agents that are on: from the URL, then the walkthrough turns more on
  let guided = false; // the walkthrough is in charge of which agents are on; until it starts, a Dispute with photos gets its photos analysed
  const ticked = () => SWITCHES.filter((s) => (on.has(s.name) || (s.name === "routing" && safetyIncident) || (s.needsPhotos && !guided && !params.has("core"))) && (!s.needsPhotos || photosOnHand)).map((s) => s.name);
  const variantSuffix = () => ticked().filter((name) => !SWITCHES.find((s) => s.name === name).liveOnly).map((name) => `.${name}`).join(""); // the recorded stream for this setting
  const switchQuery = () => ticked().map((name) => `${name}=true`).join("&"); // the live API

  const $ = (id) => document.getElementById(id);
  $("modeBadge").textContent = isRecorded() ? "Replay" : "Live";
  $("modeBadge").classList.toggle("replay", isRecorded());
  const PACE_MS = params.has("pace") && Number.isFinite(Number(params.get("pace"))) ? Number(params.get("pace")) : 600;

  const THRESHOLD = Number(document.body.dataset.threshold) || 0.7; // below this a Ruling goes to a person
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let runId = 0; // a new run cancels the old one's timers
  let currentCase = null;

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (key === "class") node.className = value;
      else if (key.startsWith("data-") || key.startsWith("aria-")) node.setAttribute(key, value);
      else node[key] = value;
    }
    for (const child of children) if (child != null) node.append(child);
    return node;
  }

  const words = (text) => String(text).replace(/_/g, " ");
  const cap = (text) => text.charAt(0).toUpperCase() + text.slice(1);
  const clock = (iso) => new Date(iso).toLocaleTimeString("en-SG", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, timeZone: "Asia/Singapore" });
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  // --- Tabs (same pattern as the rider app: data-tab buttons toggle aria-pressed and hide the other panels) ----------

  function showTab(name) {
    document.querySelectorAll("[data-tab]").forEach((button) => {
      const selected = button.dataset.tab === name;
      button.setAttribute("aria-pressed", String(selected));
      $(button.dataset.tab).hidden = !selected;
    });
  }
  document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => showTab(button.dataset.tab)));

  // --- Running a dispute ----------------------------------------------------------------------------

  const syncPhotoSwitch = (button) => { photosOnHand = Boolean(button.dataset.photos); safetyIncident = button.dataset.category === "safety_incident"; };
  document.querySelectorAll("button.trip-choice").forEach((button) => button.addEventListener("click", () => { syncPhotoSwitch(button); run(button); }));

  // /?run=DISP-003 opens the console already running that dispute (a deep link for the demo).
  const autorun = params.get("run") && document.querySelector(`button.trip-choice[data-dispute="${params.get("run")}"]`);
  if (autorun) setTimeout(() => { syncPhotoSwitch(autorun); run(autorun); }, 0);

  function reset(button) {
    const d = button.dataset;
    $("caseMeta").textContent = `${d.when} SGT · ${words(d.category)}`;
    $("caseTitle").textContent = `${cap(words(d.category))} dispute`;
    $("caseId").textContent = `${d.dispute} · filed by the ${d.filedBy}`;
    $("caseStatus").textContent = "Running";
    $("pickup").textContent = d.pickup;
    $("destination").textContent = d.destination;
    $("fare").textContent = d.fare;
    $("fareLabel").textContent = d.category === 'route_deviation' ? 'Paid fare in dispute' : 'Fee in dispute';
    $("disputeNote").textContent = `Dispute: ${d.description}`;
    $("log").replaceChildren();
    workflow.reset();
    $("outcomes").hidden = true;
    $("outcomePair").replaceChildren();
    $("summaryCard").replaceChildren();
    $("summaryCard").hidden = true;
    $("ruling").replaceChildren(el("p", { class: "muted" }, "No ruling yet."));
    $("evidence").replaceChildren(el("p", { class: "muted" }, "The sealed evidence will appear once the run finishes."));
    $("submissions").replaceChildren(el("p", { class: "muted" }, "The submissions will appear once the run finishes."));
    $("calls").replaceChildren(el("p", { class: "muted" }, "The model calls will appear once the run finishes."));
    $("appError").hidden = true;
    showTab("overview");
  }

  async function run(button) {
    const mine = ++runId;
    const disputeId = button.dataset.dispute;
    document.querySelectorAll("button.trip-choice").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    reset(button);
    setStatus(isRecorded() ? `Replaying a recording of ${disputeId}. No model is called.` : `Running ${disputeId} on the model in the header…`);
    try {
      const source = isRecorded() ? await loadRecorded(disputeId) : await start(disputeId);
      await follow(source, mine, disputeId);
    } catch (error) {
      if (mine === runId) fail(`Could not run ${disputeId}: ${error.message}`);
    }
  }

  async function loadRecorded(disputeId) {
    const response = await fetch(`/static/recorded/${disputeId}${variantSuffix()}.json`);
    if (!response.ok) throw new Error(`no recorded stream for ${disputeId} with these settings; untick one, or run it live`);
    const body = await response.json();
    return async () => body;
  }

  async function start(disputeId) {
    const response = await fetch(`/api/disputes/${disputeId}/run${switchQuery() ? "?" + switchQuery() : ""}`, { method: "POST" });
    const started = await response.json();
    if (!response.ok) throw new Error(started.error || response.statusText);
    return async () => {
      const read = await fetch(`/api/cases/${started.case_id}`);
      if (!read.ok) throw new Error((await read.json()).error || read.statusText);
      return read.json();
    };
  }

  // Poll for the newest state, and reveal log events one at a time at the chosen replay speed.
  async function follow(fetchBody, mine, disputeId) {
    let shown = 0;
    let body = await fetchBody();
    let lastPoll = Date.now();
    while (mine === runId) {
      currentCase = body.case;
      if (shown < body.log.length) {
        appendEvent(body.log[shown++]);
        setStatus(`${isRecorded() ? "Replaying" : "Running"} ${disputeId}: ${shown} of ${body.log.length} events so far…`);
        const pace = PACE_MS;
        if (pace) await sleep(pace);
        if (!isRecorded() && Date.now() - lastPoll > POLL_MS) { body = await fetchBody(); lastPoll = Date.now(); }
        continue;
      }
      if (body.case.outcomes.length > 0 || body.run_error || body.case.status === "rejected") break;
      await sleep(POLL_MS);
      body = await fetchBody();
      lastPoll = Date.now();
    }
    if (mine !== runId) return;
    currentCase = body.case;
    markNow(null);
    workflow.finish();
    $("caseStatus").textContent = words(body.case.status);
    showPriority(body.case);
    if (body.run_error) fail(`The run stopped: ${body.run_error}`);
    else setStatus(`${disputeId} finished: ${body.log.length} events. Case ${body.case.case_id} is ${words(body.case.status)}.`);
    renderSummary(body.case, body.log);
    renderRuling(body.case);
    renderOutcomes(body.case);
    renderEvidence(body.case);
    renderSubmissions(body.case);
    renderCalls(body.calls);
    if (["ruling", "evidence", "submissions", "calls"].includes(params.get("tab"))) showTab(params.get("tab"));
  }

  function showPriority(kase) {
    const base = `${kase.dispute.dispute_id} · filed by the ${kase.dispute.filed_by}`;
    $("caseId").textContent = kase.priority_reason ? `${base} · Priority ${kase.priority}: ${kase.priority_reason}` : base;
  }

  function setStatus(text) { $("status").textContent = text; }
  function fail(text) {
    setStatus(text);
    $("appError").textContent = text;
    $("appError").hidden = false;
  }

  // --- Communication log (the rider app's .timeline) ------------------------------------------------

  function appendEvent(event) {
    const info = agentInfo(event.agent);
    const detail = event.kind === "model_call";
    const item = el("li", { class: `kind-${event.kind} agent-row ${info.accent}${detail ? " detail" : ""}` },
      el("span", { class: "agent-avatar", "aria-hidden": "true" }, icon(...info.glyph)),
      el("div", { class: "agent-body" },
        el("div", { class: "agent-head" },
          el("strong", { class: "agent-name" }, info.name),
          el("span", { class: "agent-role" }, info.role),
          el("time", { dateTime: event.timestamp }, `${clock(event.timestamp)} SGT`)),
        addressee(event) ? el("p", { class: "agent-to" }, el("span", { "aria-hidden": "true" }, "→ "), addressee(event)) : null,
        el("p", { class: "agent-summary" }, event.summary),
        event.kind === "photo_analysed" ? photoCard(event) : null,
        event.references.length ? el("div", { class: "refs" }, ...event.references.map(citeButton)) : null));
    item.dataset.nodes = workflow.event(event).join(" ");
    $("log").append(item);
    markNow(item);
    item.scrollIntoView({ block: "nearest" });
  }

  // Photo analysis made visible: the photo beside what was found, and which checks it passed. Findings are signals, never proof.
  function photoCard(event) {
    const items = event.references.map((id) => currentCase && currentCase.evidence.find((e) => e.evidence_id === id)).filter(Boolean);
    if (!items.length) return null;
    const file = items[0].derived && items[0].derived.photo;
    const verdict = (item) => {
      const d = item.derived || {};
      if (d.alignment) return { name: "Taken during the trip?", ok: d.alignment === "aligned" };
      if (d.signal) return { name: "Made by AI?", ok: d.signal === "none" };
      return { name: "What it shows", ok: null };
    };
    return el("div", { class: "photo-card" },
      file ? el("img", { class: "photo-thumb", src: photoUrl(file), alt: "Photo filed with the report (simulated placeholder)" }) : null,
      el("ul", { class: "photo-checks" }, ...items.map((item) => {
        const v = verdict(item);
        return el("li", { class: v.ok === null ? "info" : v.ok ? "pass" : "warn" },
          el("span", { class: "check-mark", "aria-hidden": "true" }, v.ok === null ? "i" : v.ok ? "✓" : "!"),
          el("div", {}, el("strong", {}, v.name), el("p", {}, item.content), item.derived.uncertainty ? el("small", {}, `Uncertainty: ${item.derived.uncertainty}`) : null));
      })));
  }

  // The log records who wrote each event, not who read it, so "to" is derived from the kind of event.
  const TO = {
    case_filed: "Intake", priority_set: "Review queue",
    evidence_requested: "Evidence agents", evidence_returned: "Both advocates", evidence_sealed: "Both advocates and the Judge", evidence_resealed: "Both advocates and the Judge",
    photo_analysed: "Evidence record", policy_retrieved: "Both advocates and the Judge", precedent_retrieved: "Both advocates and the Judge",
    submission_filed: "Judge", argument_assessed: "Judge's ruling", ruling_drafted: "Rider and Driver",
    escalated: "Human reviewer", review_decision: "Case record", outcome_sent: "Rider and Driver",
  };
  const addressee = (event) => TO[event.kind] || null;

  function markNow(item) {
    $("log").querySelectorAll("li.now").forEach((li) => li.classList.remove("now"));
    if (item) item.classList.add("now");
  }

  // --- Summary card (overview) and Ruling tab ------------------------------------------------------

  function renderSummary(kase, log) {
    const ruling = kase.ruling;
    const card = $("summaryCard");
    card.hidden = false;
    if (!ruling) {
      const why = log.filter((e) => e.kind === "escalated" || e.kind === "case_rejected").map((e) => e.summary).pop();
      card.replaceChildren(el("span", { class: "support-symbol", "aria-hidden": "true" }, "!"), el("h3", {}, "No ruling"), el("p", {}, why || `Case status: ${words(kase.status)}.`));
      return;
    }
    const seeRuling = el("button", { type: "button", class: "primary-button" }, "See the full ruling ", el("span", { "aria-hidden": "true" }, "↗"));
    seeRuling.addEventListener("click", () => showTab("ruling"));
    card.replaceChildren(...[
      el("span", { class: "support-symbol", "aria-hidden": "true" }, ruling.status === "proposal" ? "!" : "✓"),
      el("h3", {}, headline(kase)),
      el("div", { class: "badge-line" },
        el("span", { class: `chip ${ruling.status}` }, ruling.status === "proposal" ? "Proposal, held for review" : "Final"),
        el("span", { class: "chip" }, `Remedy: ${words(ruling.remedy)}`)),
      ruling.amount != null ? el("p", {}, el("span", { class: "big-number" }, `${ruling.currency} ${ruling.amount}`)) : null,
      gauge(ruling.confidence.value, ruling.status === 'proposal' || ruling.review_triggers.length > 0),
      el("p", {}, ruling.reasoning_summary),
      seeRuling].filter(Boolean)); // replaceChildren would print a null as the text "null"
  }

  function headline(kase) {
    const claimant = cap(kase.dispute.filed_by);
    if (kase.ruling.status === 'proposal') return 'Decision pending human review';
    if (kase.ruling.outcome === 'partially_uphold') return `${claimant}'s claim partially upheld`;
    return kase.ruling.outcome === "reject" ? `${claimant}'s claim rejected` : `${claimant}'s claim upheld`;
  }

  function renderRuling(kase) {
    const ruling = kase.ruling;
    if (!ruling) return;
    const parts = [
      el("p", { class: "eyebrow" }, "Ruling"),
      el("h3", { class: "verdict" }, headline(kase)),
      el("div", { class: "badge-line" },
        el("span", { class: `chip ${ruling.status}` }, ruling.status === "proposal" ? "Proposal, held for review" : "Final"),
        el("span", { class: "chip" }, `Remedy: ${words(ruling.remedy)}`)),
    ];
    if (ruling.amount != null) {
      parts.push(el("p", {}, el("span", { class: "big-number" }, `${ruling.currency} ${ruling.amount}`)));
      if (ruling.calculation) parts.push(el("p", { class: "who" }, `${ruling.calculation.formula} · from `, ...ruling.calculation.input_evidence_ids.map(citeButton)));
    }
    parts.push(el("p", {}, ruling.reasoning_summary), confidenceBlock(ruling));
    if (ruling.review_triggers.length) {
      parts.push(detail("Why it is held for review", el("ul", { class: "plain-list" },
        ...ruling.review_triggers.map((t) => el("li", {}, t.reason.startsWith("Policy Gap") ? t.reason : `${cap(words(t.trigger))}: ${t.reason}`)))));
    }
    parts.push(detail("Each argument, assessed", el("ul", { class: "assessments" }, ...ruling.argument_assessments.map(assessment))));
    if (ruling.own_findings.length) {
      parts.push(detail("Own findings", el("ul", { class: "plain-list" }, ...ruling.own_findings.map((f) => el("li", {}, f.finding + (f.decisive ? " (decisive)" : ""))))));
    }
    parts.push(detail("Material evidence", el("ul", { class: "checklist" }, ...ruling.material_evidence.map((m) =>
      el("li", { class: m.evidence_ids.length ? "" : "missing" }, `${m.evidence_ids.length ? "Available" : "Missing"}: ${m.label}`)))));
    parts.push(detail("Cited", el("div", { class: "cites" }, ...ruling.cited_evidence_ids.map(citeButton), ...ruling.cited_policy_clause_ids.map(citeButton), ...ruling.cited_precedent_ids.map(citeButton))));
    $("ruling").replaceChildren(...parts);
  }

  function confidenceBlock(ruling) {
    const { value, components } = ruling.confidence;
    const entries = Object.entries(components);
    const weakest = Math.min(...entries.map(([, v]) => v));
    const block = el("div", { class: "detail-section" },
      el("h3", {}, "Confidence"),
      gauge(value, ruling.status === 'proposal' || ruling.review_triggers.length > 0),
      el("p", { class: "who" }, "Confidence is the lowest of its parts."),
      el("ul", { class: "bars" }, ...entries.map(([name, v]) =>
        el("li", { class: `bar${v === weakest ? " weakest" : ""}` },
          el("span", { class: "name" }, cap(words(name))),
          el("span", { class: "track" }, el("span", { class: "fill", style: `width:${Math.round(v * 100)}%` })),
          el("span", { class: "num" }, v.toFixed(2))))),
      el("p", { class: "weakest-note" }, ruling.history_adjustments.length
        ? "The blue bar is the weakest part. History then lowered the score."
        : "The blue bar is the weakest part, and it sets the score."));
    for (const adjustment of ruling.history_adjustments) {
      block.append(el("p", { class: "history" }, `History lowered it by ${adjustment.confidence_step}: ${adjustment.reason}`));
    }
    return block;
  }

  function assessment(a) {
    return el("li", {},
      el("div", { class: "who" }, `${cap(words(a.author))} argued`),
      el("div", {}, el("span", { class: `verdict-tag verdict-${a.verdict}` }, words(a.verdict)), a.argument),
      el("div", { class: "who" }, a.reason),
      el("div", { class: "cites" }, ...a.evidence_ids.map(citeButton)));
  }

  function detail(title, content) {
    return el("div", { class: "detail-section" }, el("h3", {}, title), content);
  }

  // --- Outcomes (overview): rider and driver side by side ----------------------------------------------

  const ACTION_LABEL = {
    recommended: "RECOMMENDED, NOT EXECUTED",
    pending_review: "PENDING REVIEW",
    executed: "EXECUTED (SIMULATED)",
    failed: "FAILED",
  };

  function renderOutcomes(kase) {
    if (!kase.outcomes.length) return;
    const order = ["rider", "driver"];
    const cards = [...kase.outcomes].sort((a, b) => order.indexOf(a.party) - order.indexOf(b.party)).map((o) =>
      el("div", { class: `support-card outcome ${o.action_status}` },
        el("h3", {}, `${cap(o.party)} is told`),
        el("span", { class: "action" }, ACTION_LABEL[o.action_status] || words(o.action_status).toUpperCase()),
        el("p", {}, o.ruling_summary)));
    $("outcomePair").replaceChildren(...cards);
    $("outcomes").hidden = false;
  }

  // --- Evidence and policy tab, and cited-ID navigation ------------------------------------------------

  function renderEvidence(kase) {
    const available = kase.evidence.filter((e) => e.status !== "missing").length;
    const parts = [
      el("p", { class: "eyebrow" }, `Sealed evidence · version ${kase.evidence_version || "none"}`),
      el("div", { class: "section-title" }, el("h3", {}, `${available} available · ${kase.evidence.length - available} missing`)),
      ...(kase.dispute.photos.length ? [photosFiled(kase)] : []),
      ...kase.evidence.map(evidenceItem),
      el("div", { class: "section-title" }, el("h3", {}, `Policy clauses (${kase.policy_clauses.length})`)),
      ...kase.policy_clauses.map(clauseItem),
      ...(kase.switches.policy_precedent ? [
        el("div", { class: "section-title" }, el("h3", {}, kase.precedents.length ? `Similar precedents (${kase.precedents.length}, advisory)` : "Precedents: none found for this Case")),
        ...kase.precedents.map(precedentItem),
      ] : []),
    ];
    $("evidence").replaceChildren(...parts);
  }

  // Photos filed with the report, shown whether or not the photo analysis switch is on; findings come only with it.
  const photoUrl = (path) => `/photos/${String(path).split("/").pop()}`;
  function photosFiled(kase) {
    const analysed = kase.evidence.some((e) => e.source === "photo_finding");
    return el("div", { class: "photos-filed" },
      el("div", { class: "section-title" }, el("h3", {}, `Photos filed (${kase.dispute.photos.length})`)),
      el("p", { class: "muted small" }, analysed ? "Findings below are signals with stated uncertainty, never proof." : "Not analysed: photo analysis is off, so the Judge sees no findings and Confidence is lower."),
      el("div", { class: "photo-row" }, ...kase.dispute.photos.map((p) => el("img", { class: "evidence-photo", src: photoUrl(p), alt: "Photo filed with the report (simulated placeholder)" }))));
  }

  function evidenceItem(item) {
    const derived = Object.entries(item.derived || {});
    const body = el("div", { class: "evidence-body" });
    if (item.status === "missing") body.append(el("p", { class: "missing-note" }, "This item is missing. It can be cited only as missing, never as fact."));
    if (item.derived && item.derived.uncertainty) body.append(el("p", { class: "uncertainty" }, `Uncertainty: ${item.derived.uncertainty}`));
    body.append(el("dl", {},
      el("dt", {}, "Source"), el("dd", {}, item.source),
      el("dt", {}, "Side"), el("dd", {}, item.side),
      ...derived.flatMap(([k, v]) => [el("dt", {}, words(k)), el("dd", {}, typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v))])));
    const hasContent = item.content != null && !(typeof item.content === "object" && !Object.keys(item.content).length);
    if (hasContent) body.append(el("pre", {}, typeof item.content === "string" ? item.content : JSON.stringify(item.content, null, 2)));
    return el("details", { class: "evidence-item", id: `item-${item.evidence_id}` },
      el("summary", {}, el("span", {}, `${item.evidence_id} · ${words(item.source)}`), el("span", { class: `state ${item.status}` }, item.status)),
      body);
  }

  function clauseItem(clause) {
    return el("details", { class: "evidence-item", id: `item-${clause.clause_id}` },
      el("summary", {}, el("span", {}, `${clause.clause_id} · ${words(clause.category)}`), el("span", { class: "state" }, `v ${clause.version}`)),
      el("div", { class: "evidence-body" }, el("p", {}, clause.text)));
  }

  function precedentItem(p) {
    const r = p.ruling;
    return el("details", { class: "evidence-item", id: `item-${p.precedent_id}` },
      el("summary", {}, el("span", {}, `${p.precedent_id} · ${words(r.outcome)} · ${words(r.remedy)}`), el("span", { class: "state" }, words(p.source))),
      el("div", { class: "evidence-body" },
        el("p", {}, p.case_summary),
        el("p", { class: "who" }, `Similar because: ${p.similarity_tags.map(words).join(", ")}`),
        el("p", {}, el("strong", {}, "Reasoning then: "), r.reasoning_summary),
        el("p", { class: "who" }, `Policy cited: ${r.cited_policy_clause_ids.join(", ")}`)));
  }

  function citeButton(id) {
    const button = el("button", { type: "button", class: "cite" }, id);
    button.addEventListener("click", () => { hideCard(); goTo(id); });
    button.addEventListener("mouseenter", () => showCard(id, button));
    button.addEventListener("focus", () => showCard(id, button));
    button.addEventListener("mouseleave", hideCard);
    button.addEventListener("blur", hideCard);
    return button;
  }

  // An ID opens its Evidence Item or Policy Clause on the Evidence and policy tab.
  function goTo(id) {
    const target = document.getElementById(`item-${id}`);
    if (!target) return;
    showTab("evidence");
    target.open = true;
    target.classList.add("flash");
    target.scrollIntoView({ block: "center" });
    setTimeout(() => target.classList.remove("flash"), 1600);
  }

  // --- Submissions tab -------------------------------------------------------------------------------

  function renderSubmissions(kase) {
    if (!kase.submissions.length) { $("submissions").replaceChildren(el("p", { class: "muted" }, "No submissions were filed.")); return; }
    $("submissions").replaceChildren(...kase.submissions.map((s) => el("div", { class: "submission" },
      el("p", { class: "eyebrow" }, cap(words(s.author))),
      el("h3", {}, s.claim_restated),
      el("p", { class: "who" }, "Facts relied on"),
      el("div", { class: "cites" }, ...s.facts_relied_on.map(citeButton), ...s.missing_evidence_ids.map(citeButton)),
      ...s.counter_arguments.flatMap((c) => [el("p", {}, el("strong", {}, "Counter-argument: "), c.argument), el("p", {}, el("strong", {}, "Response: "), c.response)]),
      el("p", { class: "who" }, "Policy clauses cited"),
      el("div", { class: "cites" }, ...s.policy_clause_ids.map(citeButton)),
      el("p", {}, el("strong", {}, "Asks for: "), s.requested_outcome))));
  }


  // --- Model calls tab: every request to the model, on a timeline, with its prompt and reply -----------------------

  const AGENT_NAMES = { rider_advocate: "Rider advocate", driver_advocate: "Driver advocate", judge: "Judge", judge_self_check: "Judge self-check" };
  const agentName = (agent) => AGENT_NAMES[agent] || cap(words(agent));

  function renderCalls(calls) {
    if (!calls || !calls.length) { $("calls").replaceChildren(el("p", { class: "muted" }, "No model calls were made.")); return; }
    const starts = calls.map((c) => Date.parse(c.started_at));
    const ends = calls.map((c, i) => starts[i] + c.seconds * 1000);
    const origin = Math.min(...starts), span = Math.max(Math.max(...ends) - origin, 1);
    const retries = calls.filter((c) => c.sent_back_because).length, failed = calls.filter((c) => c.outcome !== "ok").length;
    const total = calls.reduce((sum, c) => sum + c.seconds, 0);

    const lanes = calls.map((c, i) => el("li", { class: "lane" },
      el("span", { class: "lane-name" }, `${agentName(c.agent)} · call ${c.attempt}`),
      el("span", { class: "lane-track" }, el("span", { class: `lane-bar ${c.outcome}${c.sent_back_because ? " retry" : ""}`,
        style: `left:${(((starts[i] - origin) / span) * 100).toFixed(2)}%;width:max(${((c.seconds * 1000 / span) * 100).toFixed(2)}%,6px)` })),
      el("span", { class: "lane-time" }, `${c.seconds.toFixed(1)}s`)));

    const cards = calls.map((c) => el("details", { class: `evidence-item call ${c.outcome}` },
      el("summary", {},
        el("span", {}, `#${c.index} · ${agentName(c.agent)} · call ${c.attempt}`),
        el("span", { class: "call-meta" }, `${c.model} · ${c.seconds.toFixed(1)}s`),
        el("span", { class: `state call-${c.outcome}` }, c.sent_back_because ? "retry" : c.outcome === "ok" ? "replied" : c.outcome)),
      el("div", { class: "evidence-body" },
        c.sent_back_because ? el("p", { class: "missing-note" }, `Sent back because: ${c.sent_back_because}`) : null,
        c.problem ? el("p", { class: "missing-note" }, c.problem) : null,
        ...c.messages.map((m) => el("div", { class: "msg" }, el("p", { class: "who" }, `${m.role} sent`), el("pre", {}, m.content))),
        c.reply ? el("div", { class: "msg" }, el("p", { class: "who" }, "reply received"), el("pre", {}, c.reply)) : null)));

    $("calls").replaceChildren(
      el("p", { class: "eyebrow" }, "Every request to the model"),
      el("div", { class: "section-title" }, el("h3", {}, `${calls.length} calls · ${retries} sent back · ${failed} not clean · ${total.toFixed(1)}s of model time`)),
      el("ol", { class: "lanes", "aria-label": "Timeline of model calls" }, ...lanes),
      el("p", { class: "who" }, "Calls that overlap ran at the same time. Open a call to read the exact prompt and reply."),
      ...cards);
  }

  // --- SVG helpers ---------------------------------------------------------------------------------------

  const SVGNS = "http://www.w3.org/2000/svg";
  function svg(tag, attrs = {}, ...children) {
    const node = document.createElementNS(SVGNS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    for (const child of children) if (child != null) node.append(child);
    return node;
  }
  const icon = (...paths) => svg("svg", { viewBox: "0 0 24 24", width: 18, height: 18, fill: "none", stroke: "currentColor",
    "stroke-width": 2, "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" },
    ...paths.map((d) => svg("path", { d })));
  // --- Confidence gauge ----------------------------------------------------------------------------------
  // Ported from the 21st.dev "Financial Score Cards" (designali-in/financial-score-cards): a half-circle arc with a
  // gradient by strength, a strength badge, digits that slide up, and an arc that holds, then sweeps on a slow ease.
  // The escalation line is our addition: a tick where a Ruling goes to a person.

  const STRENGTH_COLORS = {
    strong: ["hsl(142, 71%, 80%)", "hsl(142, 71%, 60%)", "hsl(142, 71%, 40%)"],
    moderate: ["hsl(38, 92%, 80%)", "hsl(38, 92%, 60%)", "hsl(38, 92%, 40%)"],
    weak: ["hsl(0, 84%, 80%)", "hsl(0, 84%, 60%)", "hsl(0, 84%, 40%)"],
  };
  let gradientCount = 0;

  function gauge(value, heldForReview = false) {
    const R = 45, CX = 50, CY = 50.5, half = Math.PI * R;
    const strength = value >= 0.8 ? "strong" : value >= 0.4 ? "moderate" : "weak";
    const below = value < THRESHOLD;
    const reviewText = heldForReview ? 'A review trigger requires a person to review this proposal, regardless of the confidence line.' : below ? `Below the ${THRESHOLD} line: a person reviews this.` : `At or above the ${THRESHOLD} line: no review needed.`;
    const gradientId = `gauge-gradient-${++gradientCount}`;
    const arc = `M${CX - R} ${CY} A${R} ${R} 0 0 1 ${CX + R} ${CY}`;
    const target = half * (1 - Math.min(value, 1));
    const fill = svg("path", { d: arc, class: "gauge-fill", stroke: `url(#${gradientId})`, "stroke-dasharray": half, "stroke-dashoffset": reducedMotion ? target : half });
    if (!reducedMotion && fill.animate) {
      fill.animate(
        [{ strokeDashoffset: half, offset: 0 }, { strokeDashoffset: half, offset: 400 / 1400 }, { strokeDashoffset: target }],
        { duration: 1400, easing: "cubic-bezier(0.65, 0, 0.35, 1)", fill: "forwards" });
    } else {
      fill.setAttribute("stroke-dashoffset", target); // no animation support: show the value at once
    }
    const angle = Math.PI * THRESHOLD;
    const tick = svg("line", {
      x1: CX - (R - 9) * Math.cos(angle), y1: CY - (R - 9) * Math.sin(angle),
      x2: CX - (R + 7) * Math.cos(angle), y2: CY - (R + 7) * Math.sin(angle), class: "gauge-tick" });
    const dial = svg("svg", { viewBox: "0 0 100 52", class: "gauge-dial", role: "img",
      "aria-label": `Confidence ${value.toFixed(2)} out of 1, ${strength}. ${reviewText}` },
      svg("defs", {}, svg("linearGradient", { id: gradientId, x1: 0, y1: 0, x2: 1, y2: 0 },
        ...STRENGTH_COLORS[strength].map((color, i, all) => svg("stop", { offset: `${(100 / (all.length - 1)) * i}%`, "stop-color": color })))),
      svg("path", { d: arc, class: "gauge-track" }), fill, tick);
    const digits = value.toFixed(2).split("").map((ch, i) => {
      const span = el("span", { class: "digit" }, ch);
      if (!reducedMotion) { span.style.animationDelay = `${400 + i * 100}ms`; span.style.animationDuration = `${800 + i * 300}ms`; }
      return span;
    });
    return el("div", { class: "gauge" },
      el("div", { class: "gauge-head" },
        el("span", { class: "gauge-title" }, "Confidence"),
        el("span", { class: `gauge-badge ${strength}` }, strength)),
      el("div", { class: "gauge-body" }, dial,
        el("div", { class: "gauge-display" }, el("div", { class: "gauge-digits" }, ...digits), el("div", { class: "gauge-label" }, "out of 1"))),
      el("p", { class: `gauge-note${below ? " low" : ""}` },
        reviewText));
  }

  // --- Hover card: preview a cited item without leaving the tab -----------------------------------------

  const card = $("hovercard");
  function showCard(id, anchor) {
    if (!currentCase) return;
    const ev = currentCase.evidence.find((e) => e.evidence_id === id);
    const cl = currentCase.policy_clauses.find((c) => c.clause_id === id);
    const pr = currentCase.precedents.find((p) => p.precedent_id === id);
    if (!ev && !cl && !pr) return;
    if (pr) {
      card.replaceChildren(el("strong", {}, `${pr.precedent_id} · precedent (${words(pr.source)})`), el("p", {}, pr.case_summary), el("p", {}, `${words(pr.ruling.outcome)} · ${words(pr.ruling.remedy)}`));
    } else if (cl) {
      card.replaceChildren(el("strong", {}, `${cl.clause_id} · policy clause`), el("p", {}, cl.text.length > 220 ? cl.text.slice(0, 220) + "…" : cl.text));
    } else {
      const facts = Object.entries(ev.derived || {}).slice(0, 5);
      card.replaceChildren(
        el("strong", {}, `${ev.evidence_id} · ${words(ev.source)}`),
        el("span", { class: `state ${ev.status}` }, ev.status),
        ev.status === "missing" ? el("p", {}, "Missing. It can be cited only as missing.") : null,
        facts.length ? el("dl", {}, ...facts.flatMap(([k, v]) => [el("dt", {}, words(k)), el("dd", {}, String(v))])) : null);
    }
    card.append(el("p", { class: "hint" }, "Click to open"));
    card.hidden = false;
    const box = anchor.getBoundingClientRect();
    card.style.left = `${Math.max(8, Math.min(innerWidth - card.offsetWidth - 8, box.left))}px`;
    const below = box.bottom + 8;
    card.style.top = `${below + card.offsetHeight > innerHeight ? Math.max(8, box.top - card.offsetHeight - 8) : below}px`;
  }
  function hideCard() { card.hidden = true; }
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") hideCard(); });

  // --- Agent identities -------------------------------------------------------------------------------
  // Each Communication Log row is attributed to the agent that wrote it. The three Core Agents get a
  // distinct glyph and colour so the exchange reads at a glance; supporting and system writes stay neutral.

  const GLYPHS = {
    rider: ["M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2", "M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"],
    driver: ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z", "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z", "M12 3v5", "M4.3 15.5l4.4-2.5", "M19.7 15.5l-4.4-2.5"],
    judge: ["M16 16l3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z", "M2 16l3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z", "M7 21h10", "M12 3v18", "M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"],
    system: ["M22 12h-4l-3 9L9 3l-3 9H2"],
  };

  const LOG_AGENTS = {
    rider_advocate: { name: "Rider Advocate", role: "Argues the rider's case" },
    driver_advocate: { name: "Driver Advocate", role: "Argues the driver's case" },
    judge: { name: "Judge", role: "Weighs both cases and rules" },
    judge_self_check: { name: "Judge self-check", role: "Checks its own ruling" },
    judge_second_pass: { name: "Judge second pass", role: "Rules a second time, order swapped" },
    intake: { name: "Intake", role: "Files the case" },
    orchestrator: { name: "Orchestrator", role: "Runs the stages in order" },
    evidence: { name: "Evidence", role: "Retrieves trip records" },
    rider_evidence: { name: "Rider Evidence Agent", role: "Finds the rider's facts" },
    driver_evidence: { name: "Driver Evidence Agent", role: "Finds the driver's facts" },
    image_analysis: { name: "Image Analysis", role: "Assesses the photos" },
    policy: { name: "Policy", role: "Finds the applicable clauses" },
    escalation: { name: "Escalation", role: "Sends it to a person" },
    learning: { name: "Learning loop", role: "Keeps the override as precedent" },
  };

  const CORE_ACCENTS = { rider_advocate: "rider", driver_advocate: "driver", judge: "judge", judge_self_check: "judge", judge_second_pass: "judge" };

  function agentInfo(agent) {
    const known = LOG_AGENTS[agent] || { name: cap(words(agent)), role: "System" };
    const accent = CORE_ACCENTS[agent] || "system";
    return { ...known, accent, glyph: GLYPHS[accent] };
  }

  // --- Agent workflow: the whole system as an n8n-style canvas -------------------------------------------
  // Three lanes: the rider's side on top, the shared spine in the middle, the driver's side below. Boxes are
  // agents, lines are the information passing between them, and both light up from the Communication Log events
  // as they are revealed, so the canvas and the log always tell the same story.

  const NODES = [
    { id: "intake", name: "Intake", note: "Files the case", col: 0, row: 1, kind: "system" },
    { id: "sla", name: "SLA routing", note: "Sets priority", col: 0, row: 2, kind: "support" },
    { id: "image", name: "Photo analysis", note: "Reads photos", col: 1, row: 0, kind: "support" },
    { id: "evidence", name: "Evidence", note: "Pulls trip records", col: 1, row: 1, kind: "system" },
    { id: "rider_ev", name: "Rider evidence", note: "Picks rider's facts", col: 2, row: 0, kind: "support", passThrough: true },
    { id: "policy", name: "Policy & precedent", note: "Finds the rules", col: 2, row: 1, kind: "support" },
    { id: "driver_ev", name: "Driver evidence", note: "Picks driver's facts", col: 2, row: 2, kind: "support", passThrough: true },
    { id: "rider_adv", name: "Rider Advocate", note: "Argues for the rider", col: 3, row: 0, kind: "rider" },
    { id: "driver_adv", name: "Driver Advocate", note: "Argues for the driver", col: 3, row: 2, kind: "driver" },
    { id: "judge", name: "Judge", note: "Weighs both and rules", col: 4, row: 1, kind: "judge" },
    { id: "escalation", name: "Escalation", note: "Holds it for a person", col: 5, row: 0, kind: "support" },
    { id: "outcome", name: "Outcome", note: "Tells rider and driver", col: 5, row: 1, kind: "system" },
    { id: "learning", name: "Learning loop", note: "Keeps overrides", col: 5, row: 2, kind: "support" },
  ];
  // [from, to, what travels along it (shown when the line is highlighted), shape]
  const EDGES = [
    ["intake", "sla", "priority"], ["intake", "image", "photos"], ["intake", "evidence", "case"], ["image", "evidence", "findings"],
    ["evidence", "rider_ev", "records"], ["evidence", "policy", "case type"], ["evidence", "driver_ev", "records"],
    ["rider_ev", "rider_adv", "rider's facts"], ["driver_ev", "driver_adv", "driver's facts"],
    ["policy", "rider_adv", "clauses"], ["policy", "driver_adv", "clauses"],
    ["rider_adv", "judge", "submission"], ["driver_adv", "judge", "submission"],
    ["judge", "outcome", "ruling"], ["judge", "escalation", "if unsure"], ["escalation", "learning", "override", "loop"],
  ];
  // Which node an event belongs to: by what it is, then by who wrote it.
  function nodesOf(event) {
    const { agent, kind } = event;
    if (kind === "priority_set") return ["sla"];
    if (kind === "outcome_sent") return ["outcome"];
    if (kind === "escalated" || kind === "review_decision" || agent === "escalation") return ["escalation"];
    if (kind === "precedent_added" || agent === "learning") return ["learning"];
    if (kind === "photo_analysed" || agent === "image_analysis") return ["image"];
    if (agent.startsWith("rider_evidence")) return ["rider_ev"];
    if (agent.startsWith("driver_evidence")) return ["driver_ev"];
    if (agent === "evidence" || ["evidence_requested", "evidence_sealed", "evidence_resealed"].includes(kind)) return ["evidence"];
    if (agent === "policy") return ["policy"];
    if (agent === "rider_advocate") return ["rider_adv"];
    if (agent === "driver_advocate") return ["driver_adv"];
    if (agent.startsWith("judge")) return ["judge"];
    if (agent === "intake") return ["intake"];
    return [];
  }

  // --- Presenter walkthrough: the Demo Day script as steps (the table in src/api/walkthrough.py) ----------------
  // Next step turns on that step's supporting agents (they stay on, so the canvas fills up as the demo goes) and
  // runs its Dispute. ?short=1 leaves out the steps the script marks skippable, and their agents stay off.

  (() => {
    const bar = $("walkthrough");
    const all = JSON.parse(document.body.dataset.walkthrough || "[]");
    if (!all.length) return;
    const steps = params.has("short") ? all.filter((s) => !s.skippable) : all;
    let at = -1;
    const LABEL = Object.fromEntries(all.flatMap((s) => s.tick.map((name, i) => [name, s.labels[i]])));
    const prev = el("button", { type: "button", class: "wt-button", "aria-label": "Previous step" }, "‹");
    const next = el("button", { type: "button", class: "wt-button primary" }, "Start the walkthrough");
    const where = el("span", { class: "wt-where" });
    const says = el("span", { class: "wt-says" }, `${steps.length} steps: the three core agents first, then each supporting agent in turn.`);
    const using = el("span", { class: "wt-using" });
    bar.hidden = false;
    bar.append(prev, el("div", { class: "wt-text" }, el("div", { class: "wt-line" }, where, says), using), next);

    function show() {
      const step = steps[at];
      prev.disabled = at <= 0;
      next.textContent = at < 0 ? "Start the walkthrough" : at >= steps.length - 1 ? "Run again" : "Next step ›";
      if (at < 0) return;
      where.textContent = `Step ${at + 1} of ${steps.length} · ${step.dispute}`;
      says.textContent = step.says;
      using.replaceChildren(
        ...(step.labels.length ? [el("span", { class: "wt-new" }, `Turns on ${step.labels.join(", ")}`)] : []),
        el("span", { class: "wt-core" }, on.size ? `Agents on: ${[...on].map((name) => LABEL[name]).join(", ")}` : "Core agents only"),
        ...(step.override ? [el("span", { class: "wt-override" }, "Then open the ", el("a", { href: "/review", target: "_blank", rel: "noopener" }, "review queue"), " and override the proposal.")] : []));
    }

    function go(index) {
      at = (index + steps.length) % steps.length;
      guided = true;
      on.clear(); // the switches turned on by every step up to this one, so stepping back never leaves a later agent on
      steps.slice(0, at + 1).forEach((s) => s.tick.forEach((name) => on.add(name)));
      show();
      const button = document.querySelector(`button.trip-choice[data-dispute="${steps[at].dispute}"]`);
      if (button) { const folded = button.closest("details.cat-more"); if (folded) folded.open = true; syncPhotoSwitch(button); run(button); }
    }
    next.addEventListener("click", () => go(at + 1));
    prev.addEventListener("click", () => go(at - 1));
    show();
  })();

  const workflow = (() => {
    const canvas = $("wfCanvas"), edgeLayer = $("wfEdges");
    const NODE_W = 124, NODE_H = 52, ROW_H = 92, PAD_X = 14, PAD_Y = 34, LOOP_PAD = 34, MIN_W = 1000;
    const state = new Map(), edgeEls = [], nodeEls = new Map();
    let filter = null, running = false, focusNode = null; // focusNode: the box under the pointer, so its lines stand out
    const seen = new Set(), waiting = new Set(); // seen: event kinds so far; waiting: agents the run is now waiting on

    NODES.forEach((n) => {
      const glyph = GLYPHS[n.kind] || GLYPHS.system;
      const box = el("button", { type: "button", class: `wf-node ${n.kind}`, "data-node": n.id, "aria-pressed": "false", title: `${n.name}: ${n.note}. Select to filter the log.` },
        el("span", { class: "wf-icon" }, icon(...glyph)),
        el("span", { class: "wf-text" }, el("strong", {}, n.name), el("small", {}, n.note)),
        el("span", { class: "wf-count", hidden: true }, "0"));
      box.addEventListener("click", () => setFilter(filter === n.id ? null : n.id));
      for (const [on, off] of [["mouseenter", "mouseleave"], ["focus", "blur"]]) {
        box.addEventListener(on, () => { focusNode = n.id; paint(); });
        box.addEventListener(off, () => { focusNode = null; paint(); });
      }
      canvas.append(box);
      nodeEls.set(n.id, box);
    });

    function place() {
      const width = Math.max(canvas.clientWidth, MIN_W);
      const colW = (width - 2 * PAD_X - LOOP_PAD) / 6;
      const pos = (n) => ({ x: PAD_X + (n.col + 0.5) * colW, y: PAD_Y + n.row * ROW_H });
      NODES.forEach((n) => { const { x, y } = pos(n); const box = nodeEls.get(n.id); box.style.width = `${NODE_W}px`; box.style.left = `${x - NODE_W / 2}px`; box.style.top = `${y - NODE_H / 2}px`; });
      const height = PAD_Y * 2 + 2 * ROW_H + NODE_H / 2;
      canvas.style.height = `${height}px`;
      edgeLayer.setAttribute("viewBox", `0 0 ${width} ${height}`);
      edgeLayer.setAttribute("width", width);
      edgeLayer.setAttribute("height", height);
      const head = (id, cls) => svg("marker", { id, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 11, markerHeight: 11, markerUnits: "userSpaceOnUse", orient: "auto" }, svg("path", { d: "M1 1 L9 5 L1 9 z", class: `wf-arrowhead ${cls}` }));
      edgeLayer.replaceChildren(svg("defs", {}, head("wfArrow", ""), head("wfArrowLit", "lit"), head("wfArrowFlow", "flowing")));
      edgeEls.length = 0;
      const byId = Object.fromEntries(NODES.map((n) => [n.id, n]));
      EDGES.forEach(([from, to, label, shape]) => {
        const A = byId[from], B = byId[to], a = pos(A), b = pos(B);
        let d, x1, y1, x2, y2;
        if (shape === "loop") { // out of the right-hand side, round the column and back in: the override feeds the learning loop
          x1 = a.x + NODE_W / 2 + 3; y1 = a.y; x2 = b.x + NODE_W / 2 + 4; y2 = b.y;
          d = `M${x1} ${y1} C${x1 + LOOP_PAD} ${y1} ${x2 + LOOP_PAD} ${y2} ${x2} ${y2}`;
        } else if (A.col === B.col) { // same column: straight down or up
          const down = b.y > a.y;
          x1 = x2 = a.x; y1 = a.y + (down ? NODE_H / 2 + 3 : -NODE_H / 2 - 3); y2 = b.y + (down ? -NODE_H / 2 - 4 : NODE_H / 2 + 4);
          d = `M${x1} ${y1} L${x2} ${y2}`;
        } else {
          x1 = a.x + NODE_W / 2 + 3; y1 = a.y; x2 = b.x - NODE_W / 2 - 4; y2 = b.y;
          const bend = Math.max(18, (x2 - x1) / 2);
          d = `M${x1} ${y1} C${x1 + bend} ${y1} ${x2 - bend} ${y2} ${x2} ${y2}`;
        }
        const path = svg("path", { d, class: "wf-edge" });
        edgeLayer.append(path);
        const ports = [svg("circle", { cx: x1, cy: y1, r: 3.5, class: "wf-port" })];
        edgeLayer.append(...ports);
        let text = null;
        if (label) { // a small pill on the line's midpoint, shown only while the line is highlighted
          const mid = path.getPointAtLength ? path.getPointAtLength(path.getTotalLength() / 2) : { x: (x1 + x2) / 2, y: (y1 + y2) / 2 };
          const w = label.length * 6.2 + 16;
          const pill = svg("rect", { x: mid.x - w / 2, y: mid.y - 9, width: w, height: 18, rx: 9, class: "wf-pill" });
          text = svg("text", { x: mid.x, y: mid.y + 3.5, class: "wf-edge-label", "text-anchor": "middle" });
          text.textContent = label;
          edgeLayer.append(pill, text);
          ports.push(pill);
        }
        edgeEls.push({ from, to, path, text, ports });
      });
      paint();
    }

    const touched = (id) => (state.get(id)?.count || 0) > 0;
    const isActive = (id) => Boolean(state.get(id)?.active) || waiting.has(id);
    // An evidence agent that was switched off is passed through: the records still reach the advocates, past its box.
    const passed = (id) => Boolean(state.get(id)?.skipped) && NODES.find((n) => n.id === id).passThrough === true;

    function paint() {
      nodeEls.forEach((box, id) => {
        const s = state.get(id) || { count: 0 };
        box.dataset.status = s.active || waiting.has(id) ? "active" : s.count ? "done" : s.skipped ? "skipped" : "idle";
        box.classList.toggle("filtered", filter === id);
        box.setAttribute("aria-pressed", String(filter === id));
        const badge = box.querySelector(".wf-count");
        badge.hidden = !s.count;
        badge.textContent = String(s.count || 0);
      });
      edgeEls.forEach((e) => {
        const lit = (touched(e.from) || passed(e.from)) && (touched(e.to) || passed(e.to)) && !(passed(e.from) && passed(e.to));
        const flowing = touched(e.from) && isActive(e.to);
        const hot = focusNode === e.from || focusNode === e.to;
        const dim = focusNode !== null && !hot;
        e.path.classList.toggle("lit", lit);
        e.path.classList.toggle("flowing", flowing);
        e.path.classList.toggle("hot", hot);
        e.path.classList.toggle("dim", dim);
        e.path.setAttribute("marker-end", `url(#${flowing ? "wfArrowFlow" : lit ? "wfArrowLit" : "wfArrow"})`);
        e.ports.forEach((p) => { p.classList.toggle("lit", lit || flowing); p.classList.toggle("dim", dim); p.classList.toggle("show", hot && p.tagName === "rect"); });
        if (e.text) { e.text.classList.toggle("lit", lit); e.text.classList.toggle("flowing", flowing); e.text.classList.toggle("show", hot); }
      });
    }

    function setFilter(id) {
      filter = id;
      $("log").querySelectorAll("li").forEach((li) => { li.hidden = id !== null && !(li.dataset.nodes || "").split(" ").includes(id); });
      paint();
    }

    function reset() { state.clear(); seen.clear(); waiting.clear(); filter = null; running = true; paint(); }
    function event(e) {
      const ids = nodesOf(e);
      state.forEach((s) => { s.active = false; });
      ids.forEach((id) => { const s = state.get(id) || { count: 0 }; s.count += 1; s.active = true; state.set(id, s); });
      expectNext(e);
      paint();
      return ids;
    }
    // A model call takes seconds and writes nothing until it returns, so the canvas shows who the run is waiting on.
    function expectNext(e) {
      seen.add(e.kind);
      if (e.kind === "submission_filed") seen.add(`sub:${e.agent}`);
      waiting.clear();
      if (!seen.has("evidence_requested")) waiting.add("evidence");
      if (seen.has("evidence_sealed") || seen.has("policy_retrieved")) {
        if (!seen.has("sub:rider_advocate")) waiting.add("rider_adv");
        if (!seen.has("sub:driver_advocate")) waiting.add("driver_adv");
      }
      if (seen.has("sub:rider_advocate") && seen.has("sub:driver_advocate") && !seen.has("ruling_drafted")) waiting.add("judge");
      if (seen.has("ruling_drafted") && !seen.has("outcome_sent") && !seen.has("escalated")) waiting.add("outcome");
    }
    function finish() {
      running = false;
      waiting.clear();
      state.forEach((s) => { s.active = false; });
      NODES.forEach((n) => { if (!touched(n.id)) state.set(n.id, { count: 0, skipped: true }); });
      paint();
    }

    new ResizeObserver(place).observe(canvas);
    place();
    return { reset, event, finish, setFilter };
  })();
})();
