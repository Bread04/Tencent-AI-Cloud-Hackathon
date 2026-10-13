(function (root) {
  'use strict';
  // Presentation-only. The backend validates the report, creates the Case and runs it (POST /api/reports); this file
  // files the report as it was submitted, watches the Case, and shows its Ruling and Communication Log.
  const RUNNING = ['filed', 'prioritised', 'gathering_evidence', 'building_cases', 'judging'];
  const SIMULATED = 'Simulated: the trip, evidence, policy and any payment on this page are mock data. No money moves.';
  const isFinished = body => Boolean(body.run_error) || !RUNNING.includes(body.case.status);
  const words = text => text.replaceAll('_', ' ');

  function createClient(fetcher = (...args) => root.fetch(...args), {wait = ms => new Promise(resolve => setTimeout(resolve, ms)), pollMs = 400, maxPolls = 300} = {}) {
    async function call(path, options) {
      let response;
      try { response = await fetcher(path, {cache: 'no-store', credentials: 'same-origin', ...options}); }
      catch { throw new Error('The dispute service is unavailable. Start the FastAPI server (uv run uvicorn src.api.demo:app) and retry. Your report is still on this page.'); }
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw Object.assign(new Error(payload.error || 'The dispute service rejected this request.'), {status: response.status});
      return payload;
    }
    const readCase = caseId => call('/api/cases/' + encodeURIComponent(caseId), {method: 'GET'});
    return Object.freeze({
      fileReport: async report => (await call('/api/reports', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(report)})).case_id,
      readCase,
      async watch(caseId, onUpdate) {
        for (let poll = 0; poll < maxPolls; poll++) {
          const body = await readCase(caseId);
          onUpdate(body);
          if (isFinished(body)) return body;
          await wait(pollMs);
        }
        throw new Error(`Case ${caseId} is still running. Open the Case page to follow it.`);
      }
    });
  }

  // What the panel says about a Case, kept apart from the DOM so it can be checked.
  function describe(body) {
    const filed = body.case, log = body.log, ruling = filed.ruling;
    const base = {caseId: filed.case_id, status: filed.status, simulated: SIMULATED, reasons: [], amount: null};
    if (body.run_error) return {...base, headline: 'The run stopped before a Ruling', reasons: [body.run_error]};
    if (filed.status === 'rejected') {
      const rejection = [...log].reverse().find(event => event.kind === 'case_rejected');
      return {...base, headline: 'Dispute rejected', reasons: [rejection ? rejection.summary.replace(/^Dispute rejected:\s*/, '') : 'The Dispute could not be accepted.']};
    }
    if (!ruling) return {...base, headline: 'No Ruling yet'};
    const confidence = ruling.confidence ? `${ruling.confidence.value} (${Object.entries(ruling.confidence.components).map(([name, value]) => `${name} ${value}`).join(', ')})` : 'not available';
    if (ruling.status === 'proposal') return {...base, headline: 'Proposal: no final decision. Held for a human reviewer.', reasons: ruling.review_triggers.map(record => `${record.trigger}: ${record.reason}`), confidence, reasoning: ruling.reasoning_summary};
    return {...base, headline: `Ruling: ${words(ruling.outcome)} (${words(ruling.remedy)})`, amount: ruling.amount == null ? null : `${ruling.currency} ${ruling.amount}`, confidence, reasoning: ruling.reasoning_summary};
  }

  const key = (rider, trip) => `waypoint:filed-dispute:v1:${rider}:${trip}`;
  function remember(storage, riderId, tripId, caseId) { try { storage.setItem(key(riderId, tripId), caseId); } catch { /* the Case still shows; only the way back from the rider app is lost */ } }
  function recall(storage, riderId, tripId) { try { return storage.getItem(key(riderId, tripId)); } catch { return null; } }

  const node = (tag, className, text) => { const element = document.createElement(tag); if (className) element.className = className; if (text !== undefined) element.textContent = text; return element; };
  const states = new WeakMap();
  function begin(mount) { const previous = states.get(mount); if (previous) previous.active = false; const state = {active: true}; states.set(mount, state); mount.replaceChildren(); return state; }
  function dispose(mount) { const previous = states.get(mount); if (previous) previous.active = false; mount.replaceChildren(); }

  function render(mount, body, running) {
    const view = describe(body), panel = node('section', 'rider-case dispute-case');
    panel.setAttribute('aria-label', 'Your filed Dispute');
    const head = node('div', 'case-header'), title = node('div');
    title.append(node('p', 'case-eyebrow', `Dispute workflow / ${view.caseId}`), node('h3', '', running ? 'Your Dispute is being worked on…' : view.headline));
    head.append(title, node('span', 'case-badge', words(view.status)));
    panel.append(head, node('p', 'case-warning', view.simulated));
    if (running) panel.append(node('p', 'notice', `Status: ${words(view.status)}. Agents are gathering evidence and ruling; the Communication Log below fills in as they go.`));
    if (view.reasoning) panel.append(node('p', 'case-conclusion', view.reasoning));
    if (view.amount) panel.append(node('p', 'case-request', `Amount: ${view.amount} (simulated)`));
    if (view.confidence) panel.append(node('p', 'case-reference', `Confidence ${view.confidence}`));
    if (view.reasons.length) {
      const reasons = node('ul', 'case-points');
      view.reasons.forEach(reason => reasons.append(node('li', '', reason)));
      panel.append(node('h4', '', 'Why'), reasons);
    }
    const filed = body.case.dispute.filed_report;
    if (filed) {
      const original = node('details', 'case-details');
      original.append(node('summary', '', 'Your report, kept as you submitted it'), node('p', 'case-quote', filed.statement), node('p', 'case-reference', `${filed.id} · ${filed.trip.reference}`));
      panel.append(original);
    }
    const log = node('details', 'case-details dispute-log');
    log.open = true;
    log.append(node('summary', '', `Communication Log · ${body.log.length} events`));
    const list = node('ol', 'case-points');
    body.log.forEach(event => {
      const item = node('li');
      item.append(node('strong', '', `${event.agent} · ${words(event.kind)}`), node('p', '', event.summary));
      list.append(item);
    });
    log.append(list);
    panel.append(log);
    const actions = node('div', 'case-actions'), link = node('a', 'case-link', 'Open the full Case page →');
    link.href = `/cases/${encodeURIComponent(view.caseId)}`;
    actions.append(link);
    panel.append(actions);
    mount.replaceChildren(panel);
  }

  const client = createClient();
  function showError(mount, message, retry) {
    const note = node('p', 'notice error', message);
    note.setAttribute('role', 'alert');
    mount.replaceChildren(note);
    if (retry) {
      const again = node('button', 'secondary-button', 'Try again');
      again.type = 'button';
      again.onclick = retry;
      mount.append(again);
    }
  }
  async function follow(mount, state, caseId) {
    try { await client.watch(caseId, body => { if (state.active) render(mount, body, !isFinished(body)); }); }
    catch (error) { if (state.active) showError(mount, error.message, () => resume(mount, caseId)); }
  }
  // File the report exactly as submitted. `onFiled` receives the Case ID so a caller can remember it.
  async function file(mount, report, {onFiled} = {}) {
    const state = begin(mount);
    mount.append(node('p', 'notice', 'Filing your report as a Dispute…'));
    try {
      const caseId = await client.fileReport(report);
      if (!state.active) return;
      if (onFiled) onFiled(caseId);
      await follow(mount, state, caseId);
    } catch (error) {
      if (state.active) showError(mount, error.status ? `This report was not filed: ${error.message}` : error.message, () => file(mount, report, {onFiled}));
    }
  }
  async function resume(mount, caseId) {
    const state = begin(mount);
    mount.append(node('p', 'notice', `Opening ${caseId}…`));
    await follow(mount, state, caseId);
  }

  const api = Object.freeze({createClient, isFinished, describe, remember, recall, file, resume, dispose});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.DisputePanel = api;
})(typeof window !== 'undefined' ? window : globalThis);
