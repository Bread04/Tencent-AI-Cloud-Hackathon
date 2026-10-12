// Demo Day console. Reads the JSON API (or a recorded stream with ?recorded=1) and fills in the rider app's trip panel.
// Everything is built with textContent, never innerHTML, so case text cannot inject markup.
(() => {
  "use strict";

  const params = new URLSearchParams(location.search);
  const recorded = params.has("recorded"); // replay /static/recorded/<dispute>.json instead of calling the orchestrator
  const POLL_MS = 400;
  // Every `input[data-switch]` is a demo switch (the table is in src/api/demo_switches.py). `?name=1` ticks it.
  const switchBoxes = [...document.querySelectorAll("input[data-switch]")];
  switchBoxes.forEach((box) => { box.checked = params.has(box.dataset.switch); });
  const ticked = () => switchBoxes.filter((box) => box.checked).map((box) => box.dataset.switch);
  const variantSuffix = () => ticked().map((name) => `.${name}`).join(""); // the recorded stream for this setting
  const switchQuery = () => ticked().map((name) => `${name}=true`).join("&"); // the live API

  const $ = (id) => document.getElementById(id);
  const paceEl = $("pace");
  if (params.get("pace") !== null && [...paceEl.options].some((o) => o.value === params.get("pace"))) paceEl.value = params.get("pace");

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

  document.querySelectorAll("button.trip-choice").forEach((button) => button.addEventListener("click", () => run(button)));

  // /?run=DISP-003 opens the console already running that dispute (a deep link for the demo).
  const autorun = params.get("run") && document.querySelector(`button.trip-choice[data-dispute="${params.get("run")}"]`);
  if (autorun) setTimeout(() => run(autorun), 0);

  function reset(button) {
    const d = button.dataset;
    $("caseMeta").textContent = `${d.when} SGT · ${words(d.category)}`;
    $("caseTitle").textContent = `${cap(words(d.category))} dispute`;
    $("caseId").textContent = `${d.dispute} · filed by the ${d.filedBy}`;
    $("caseStatus").textContent = "Running";
    $("pickup").textContent = d.pickup;
    $("destination").textContent = d.destination;
    $("fare").textContent = d.fare;
    $("disputeNote").textContent = `Dispute: ${d.description}`;
    $("log").replaceChildren();
    setProgress(-1);
    $("outcomes").hidden = true;
    $("outcomePair").replaceChildren();
    $("summaryCard").replaceChildren(el("span", { class: "support-symbol", "aria-hidden": "true" }, "…"), el("h3", {}, "Running"), el("p", {}, "The ruling will appear here as soon as the Judge has made it."));
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
    setStatus(`Running ${disputeId}…`);
    try {
      const source = recorded ? await loadRecorded(disputeId) : await start(disputeId);
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
        setStatus(`Running ${disputeId}: ${shown} of ${body.log.length} events so far…`);
        const pace = Number(paceEl.value);
        if (pace) await sleep(pace);
        if (!recorded && Date.now() - lastPoll > POLL_MS) { body = await fetchBody(); lastPoll = Date.now(); }
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
    completePipeline(body.case);
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
    const item = el("li", { class: `kind-${event.kind}` },
      el("strong", {}, cap(words(event.kind))),
      el("p", {}, event.summary),
      el("span", { class: "agent" }, `${words(event.agent)} · `),
      el("time", { dateTime: event.timestamp }, `${clock(event.timestamp)} SGT`),
      event.references.length ? el("div", { class: "refs" }, ...event.references.map(citeButton)) : null);
    $("log").append(item);
    markNow(item);
    advance(event.kind === "model_call" ? event.agent : event.kind);
    item.scrollIntoView({ block: "nearest" });
  }

  function markNow(item) {
    $("log").querySelectorAll("li.now").forEach((li) => li.classList.remove("now"));
    if (item) item.classList.add("now");
  }

  // --- Summary card (overview) and Ruling tab ------------------------------------------------------

  function renderSummary(kase, log) {
    const ruling = kase.ruling;
    const card = $("summaryCard");
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
      gauge(ruling.confidence.value, ruling.review_triggers.length > 0),
      el("p", {}, ruling.reasoning_summary),
      seeRuling].filter(Boolean)); // replaceChildren would print a null as the text "null"
  }

  function headline(kase) {
    const claimant = cap(kase.dispute.filed_by);
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
      gauge(value, ruling.review_triggers.length > 0),
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

  function evidenceItem(item) {
    const derived = Object.entries(item.derived || {});
    const body = el("div", { class: "evidence-body" });
    if (item.status === "missing") body.append(el("p", { class: "missing-note" }, "This item is missing. It can be cited only as missing, never as fact."));
    body.append(el("dl", {},
      el("dt", {}, "Source"), el("dd", {}, item.source),
      el("dt", {}, "Side"), el("dd", {}, item.side),
      ...derived.flatMap(([k, v]) => [el("dt", {}, words(k)), el("dd", {}, String(v))])));
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

  // --- Pipeline stepper ---------------------------------------------------------------------------------
  // Ported from the 21st.dev "Animated Progress Stepper" (shadcnspace/stepper-03): a spring-style progress line, a
  // travelling dot, a pulsing ring on the active step and an icon-to-check morph. Drawn in Waypoint colours.

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
  const STAGES = [
    { name: "Intake", icon: () => icon("M22 12h-6l-2 3h-4l-2-3H2", "M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z") },
    { name: "Evidence", icon: () => icon("M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z", "m21 21-4.3-4.3") },
    { name: "Policy", icon: () => icon("M4 19.5A2.5 2.5 0 0 1 6.5 17H20", "M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z") },
    { name: "Advocates", icon: () => icon("M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2", "M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z", "M22 21v-2a4 4 0 0 0-3-3.87", "M16 3.13a4 4 0 0 1 0 7.75") },
    { name: "Judge", icon: () => icon("M12 3v18", "M5 8l-3 7a4 4 0 0 0 6 0L5 8z", "M19 8l-3 7a4 4 0 0 0 6 0l-3-7z", "M7 21h10", "M5 8h14") },
    { name: "Outcome", icon: () => icon("M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z", "M4 22v-7") },
  ];
  const STAGE_OF = {
    case_filed: 0, priority_set: 0, case_rejected: 0,
    evidence_requested: 1, evidence_returned: 1, evidence_sealed: 1, photo_analysed: 1,
    policy_retrieved: 2, precedent_retrieved: 2,
    submission_filed: 3,
    argument_assessed: 4, ruling_drafted: 4, self_check_passed: 4, self_check_failed: 4, stability_check: 4,
    escalated: 5, review_decision: 5, outcome_sent: 5, precedent_added: 5,
  };
  const STAGE_OF_AGENT = { rider_advocate: 3, driver_advocate: 3, judge: 4, judge_self_check: 4 }; // a model call counts toward its agent's stage
  let reached = -1;

  function setProgress(index, finished = false, review = false) {
    reached = index;
    const last = STAGES.length - 1;
    const progress = finished ? 1 : Math.max(index, 0) / last;
    const existing = $("pipeline").querySelector(".stepper");
    const steps = STAGES.map((stage, i) => {
      const done = finished || i < index;
      const current = !finished && i === index;
      const held = review && i === last;
      const face = done ? (held ? el("span", { class: "face pop", key: "held" }, "!") : el("span", { class: "face pop" }, check()))
        : el("span", { class: "face" }, stage.icon());
      return el("li", { class: `step${done ? " done" : ""}${current ? " current" : ""}${held ? " review" : ""}`, "aria-current": current ? "step" : "false" },
        el("span", { class: "circle" }, current ? el("span", { class: "ring", "aria-hidden": "true" }) : null, face),
        el("span", { class: "step-name" }, held ? "Held for review" : stage.name));
    });
    if (existing) {
      existing.style.setProperty("--p", String(progress)); // the line and the dot ease to the new position
      existing.querySelector("ol").replaceChildren(...steps);
      return;
    }
    const stepper = el("div", { class: "stepper" },
      el("span", { class: "stepper-track" }), el("span", { class: "stepper-line" }), el("span", { class: "stepper-dot" }),
      el("ol", {}, ...steps));
    stepper.style.setProperty("--p", String(progress));
    $("pipeline").replaceChildren(stepper);
  }
  const check = () => svg("svg", { viewBox: "0 0 24 24", width: 18, height: 18, fill: "none", stroke: "currentColor", "stroke-width": 3,
    "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" }, svg("path", { d: "M20 6 9 17l-5-5" }));
  function advance(kind) {
    const stage = STAGE_OF[kind] ?? STAGE_OF_AGENT[kind];
    if (stage !== undefined && stage > reached) setProgress(stage);
  }
  function completePipeline(kase) {
    setProgress(STAGES.length - 1, true, kase.status === "pending_review" || !kase.ruling || kase.ruling.status === "proposal");
  }

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

  function gauge(value, held = false) {
    const R = 45, CX = 50, CY = 50.5, half = Math.PI * R;
    const strength = value >= 0.8 ? "strong" : value >= 0.4 ? "moderate" : "weak";
    const below = value < THRESHOLD;
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
      "aria-label": `Confidence ${value.toFixed(2)} out of 1, ${strength}. ${below ? "Below" : "At or above"} the ${THRESHOLD} line where a person reviews.` },
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
        below ? `Below the ${THRESHOLD} line: a person reviews this.`
          : held ? `Above the ${THRESHOLD} line, but held for review for another reason.`
          : `At or above the ${THRESHOLD} line: no review needed.`));
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
})();
