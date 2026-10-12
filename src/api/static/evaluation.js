// Evaluation page: run every mock case, then show the table, the pass rate and which model made it. textContent only.
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const POLL_MS = 1500;
  let timer = null;

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (key === "class") node.className = value;
      else if (key.startsWith("aria-") || key === "role") node.setAttribute(key, value);
      else node[key] = value;
    }
    for (const child of children) if (child != null) node.append(child);
    return node;
  }

  async function refresh() {
    const body = await (await fetch("/api/evaluation")).json();
    const button = $("runEval");
    button.disabled = body.state === "running";
    if (body.state === "running") {
      $("evalNote").textContent = "Running every case. A live model can take several minutes; this page updates when it finishes.";
      $("evalNote").className = "notice";
      if (!timer) timer = setInterval(refresh, POLL_MS);
      return;
    }
    clearInterval(timer); timer = null;
    if (body.state === "failed") {
      $("evalNote").textContent = `The evaluation could not finish: ${body.error}`;
      $("evalNote").className = "notice error";
    } else if (body.state === "done") {
      $("evalNote").hidden = true;
      show(body.report);
    }
  }

  function show(report) {
    $("evalModel").textContent = `Produced by: ${report.model}`;
    $("evalWhen").textContent = `Ran ${new Date(report.ran_at).toLocaleString("en-SG", { timeZone: "Asia/Singapore" })} SGT`;
    const summary = $("evalSummary");
    summary.hidden = false;
    summary.className = `eval-summary ${report.passed === report.total ? "all" : "some"}`;
    summary.replaceChildren(
      el("span", { class: "eval-rate" }, `${Math.round(report.rate * 100)}%`),
      el("span", {}, `${report.passed} of ${report.total} cases match their expected outcome`),
      el("span", { class: "who" }, /scripted/i.test(report.model)
        ? "This is the scripted stub. It proves the pipeline is wired; it does not test a model's judgement."
        : "This is a real model: these results show how it judges the prepared cases."));
    const head = el("div", { class: "eval-row eval-head", role: "row" }, ...["Case", "Expected", "Actual", "Confidence", "Result"].map((t) => el("span", { role: "columnheader" }, t)));
    const rows = report.rows.map((row) => el("div", { class: `eval-row ${row.passed ? "pass" : "fail"}`, role: "row" },
      el("span", { role: "cell" }, el("strong", {}, row.dispute_id), row.scenario ? el("small", {}, row.scenario.replace(/_/g, " ")) : null),
      el("span", { role: "cell" }, row.expected),
      el("span", { role: "cell" }, row.actual, row.why ? el("small", { class: "why" }, row.why) : null),
      el("span", { role: "cell", class: "num" }, row.confidence == null ? "–" : row.confidence.toFixed(2)),
      el("span", { role: "cell" }, el("span", { class: `result ${row.passed ? "pass" : "fail"}` }, row.passed ? "Pass" : "Fail"))));
    $("evalTable").replaceChildren(head, ...rows);
  }

  $("runEval").addEventListener("click", async () => {
    $("runEval").disabled = true;
    const response = await fetch("/api/evaluation/run", { method: "POST" });
    if (!response.ok) { $("evalNote").textContent = (await response.json()).error; $("evalNote").className = "notice error"; $("evalNote").hidden = false; }
    $("evalNote").hidden = false;
    refresh();
  });

  refresh();
})();
