// Reviewer screen: the queue of held Cases, the review package, and confirm or override. Built with textContent only.
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const POLL_MS = 4000;
  let selected = null; // the Case ID open in the panel

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

  // --- The queue ------------------------------------------------------------------------------------------

  async function loadQueue() {
    const { cases } = await (await fetch("/api/review")).json();
    $("queueCount").textContent = cases.length;
    $("queueEmpty").hidden = cases.length > 0;
    $("queue").replaceChildren(...cases.map((item) => {
      const button = el("button", { type: "button", class: "trip-choice", "aria-pressed": String(item.case_id === selected) },
        el("span", { class: "row" }, el("strong", {}, item.dispute_id), el("span", { class: "tag cancelled" }, item.awaiting_proposal ? "awaiting proposal" : item.priority ? `priority ${item.priority}` : (item.confidence == null ? "no ruling" : `confidence ${item.confidence.toFixed(2)}`))),
        el("span", { class: "journey" }, `${item.case_id}`, el("small", {}, item.reasons.map((r) => words(r.trigger)).join(" · ") || "held for review")),
        el("span", { class: "small muted" }, (item.safety_officer ? "Safety Officer · " : "") + (item.proposed_outcome ? `Proposed: ${words(item.proposed_outcome)}` : item.awaiting_proposal ? "The Judge is still drafting its proposal" : "Nothing proposed: a stage failed")),
        item.priority_reason ? el("span", { class: "small muted" }, item.priority_reason) : null);
      button.addEventListener("click", () => open(item.case_id));
      return button;
    }));
    return cases;
  }

  // --- The review package ---------------------------------------------------------------------------------

  async function open(caseId) {
    selected = caseId;
    const response = await fetch(`/api/review/${caseId}`);
    const pack = await response.json();
    if (!response.ok) { $("package").replaceChildren(el("p", { class: "notice error" }, pack.error)); return; }
    $("reviewMeta").textContent = `${cap(words(pack.dispute.category))} · filed by the ${pack.dispute.filed_by}`;
    $("reviewTitle").textContent = `${pack.dispute.dispute_id} needs a decision`;
    $("reviewId").textContent = pack.case_id;
    $("reviewStatus").textContent = words(pack.status);
    const decision = pack.status === "pending_review" ? form(pack) : null; // right under the proposal, so no scrolling to decide
    const parts = [reasons(pack), proposed(pack), decision, submissions(pack), evidence(pack)];
    $("package").replaceChildren(...parts.filter(Boolean));
    loadQueue();
  }

  function section(title, ...content) {
    return el("div", { class: "detail-section" }, el("h3", {}, title), ...content);
  }

  function reasons(pack) {
    return section("Why it is held", el("ul", { class: "plain-list" },
      ...pack.reasons.map((r) => el("li", {}, el("span", { class: "chip proposal" }, words(r.trigger)), " ", r.reason))));
  }

  function proposed(pack) {
    const ruling = pack.proposed_ruling;
    if (!ruling && pack.status !== "pending_review") return section("Proposed ruling", el("p", { class: "notice" }, "The Judge is still drafting its proposal. It will appear here when it is ready, and the decision form opens then."));
    if (!ruling) return section("Proposed ruling", el("p", { class: "notice" }, "There is no proposed ruling: a stage failed before one was made. It cannot be confirmed or overridden here."));
    const amount = ruling.amount != null ? ` · ${ruling.currency} ${ruling.amount}` : "";
    return section("Proposed ruling",
      el("p", {}, el("strong", {}, `${cap(words(ruling.outcome))}`), ` · ${words(ruling.remedy)}${amount} · confidence ${ruling.confidence ? ruling.confidence.value.toFixed(2) : "n/a"} · ${words(ruling.balance_of_evidence)} evidence`),
      pack.dispute.category === "safety_incident" ? el("p", { class: "notice" }, "Fare remedy only. The system does not rule on whether the driver's conduct was dangerous: that is for the Safety Officer to investigate.") : null,
      el("p", {}, ruling.reasoning_summary),
      ruling.cited_policy_clause_ids.length ? el("p", { class: "who" }, `Policy cited: ${ruling.cited_policy_clause_ids.join(", ")}`) : null);
  }

  function submissions(pack) {
    if (!pack.submissions.length) return section("Submissions", el("p", { class: "muted" }, "No submissions were filed."));
    return section("Both submissions", ...pack.submissions.map((s) => el("div", { class: "submission" },
      el("p", { class: "eyebrow" }, cap(words(s.author))),
      el("h3", {}, s.claim_restated),
      ...s.counter_arguments.flatMap((c) => [el("p", {}, el("strong", {}, "Counter-argument: "), c.argument), el("p", {}, el("strong", {}, "Response: "), c.response)]),
      el("p", { class: "who" }, `Relies on: ${s.facts_relied_on.join(", ") || "nothing cited"} · policy: ${s.policy_clause_ids.join(", ") || "none"}`),
      el("p", {}, el("strong", {}, "Asks for: "), s.requested_outcome))));
  }

  function evidence(pack) {
    const items = pack.evidence.map((item) => el("details", { class: "evidence-item" },
      el("summary", {}, el("span", {}, `${item.evidence_id} · ${words(item.source)}`), el("span", { class: `state ${item.status}` }, item.status)),
      el("div", { class: "evidence-body" }, el("pre", {}, JSON.stringify({ derived: item.derived, content: item.content }, null, 2)))));
    const clauses = pack.policy_clauses.map((clause) => el("details", { class: "evidence-item" },
      el("summary", {}, el("span", {}, `${clause.clause_id} · ${words(clause.category)}`), el("span", { class: "state" }, `v ${clause.version}`)),
      el("div", { class: "evidence-body" }, el("p", {}, clause.text))));
    return section("Evidence and policy", ...items, ...clauses);
  }

  // --- The decision ---------------------------------------------------------------------------------------

  function form(pack) {
    if (!pack.proposed_ruling) return null;
    const reviewer = el("input", { id: "reviewer", type: "text", placeholder: "Your name", autocomplete: "name" });
    const reason = el("textarea", { id: "reason", rows: 3, placeholder: "Why are you overriding the proposal? Required for an override." });
    const mode = (value, label) => el("label", { class: "choice" }, el("input", { type: "radio", name: "decision", value }), ` ${label}`);
    const confirm = mode("confirm", "Confirm the proposed ruling");
    const override = mode("override", "Override: reverse the outcome");
    confirm.querySelector("input").checked = true;
    const submit = el("button", { type: "submit", class: "primary-button" }, "Record the decision");
    const message = el("p", { class: "notice error", role: "alert", hidden: true });
    const sync = () => {
      const overriding = override.querySelector("input").checked;
      reason.required = overriding;
      reason.parentElement.hidden = !overriding;
    };
    const f = el("form", { class: "review-form" },
      el("h3", {}, "Your decision"),
      el("label", { class: "field" }, el("span", {}, "Reviewer"), reviewer),
      el("div", { class: "choices" }, confirm, override),
      el("label", { class: "field", hidden: true }, el("span", {}, "Reason (recorded with the case)"), reason),
      message, submit);
    f.addEventListener("change", sync);
    f.addEventListener("submit", async (event) => {
      event.preventDefault();
      const decision = f.querySelector("input[name=decision]:checked").value;
      submit.disabled = true;
      const response = await fetch(`/api/review/${pack.case_id}/decision`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewer: reviewer.value, decision, reason: reason.value }),
      });
      const body = await response.json();
      submit.disabled = false;
      if (!response.ok) { message.textContent = body.error || "The decision was refused."; message.hidden = false; return; }
      done(body.case);
    });
    return el("div", { class: "detail-section" }, f);
  }

  function done(kase) {
    const outcomes = kase.outcomes.map((o) => el("div", { class: `support-card outcome ${o.action_status}` },
      el("h3", {}, `${cap(o.party)} is told`), el("span", { class: "action" }, "RECOMMENDED, NOT EXECUTED"), el("p", {}, o.ruling_summary)));
    $("reviewStatus").textContent = words(kase.status);
    $("package").replaceChildren(
      el("div", { class: "detail-section" },
        el("h3", {}, `Decision recorded: ${words(kase.review_record.decision)}`),
        el("p", {}, `${kase.review_record.reviewer} ${kase.review_record.decision === "confirm" ? "confirmed" : "overrode"} the proposal. Final ruling: ${words(kase.ruling.outcome)}${kase.ruling.amount != null ? `, ${kase.ruling.currency} ${kase.ruling.amount}` : ""}.`),
        kase.review_record.reason ? el("p", {}, el("strong", {}, "Reason: "), kase.review_record.reason) : null),
      el("div", { class: "split" }, ...outcomes));
    selected = null;
    loadQueue();
  }

  loadQueue().then((cases) => { const wanted = new URLSearchParams(location.search).get("case"); if (wanted) open(wanted); else if (cases.length) open(cases[0].case_id); });
  setInterval(loadQueue, POLL_MS);
})();
