(function (root) {
  'use strict';
  const BASE = '/api/rider-chat/transcripts';
  let mutationQueue = Promise.resolve();
  function transaction(action) {
    const run = () => root.navigator?.locks?.request ? root.navigator.locks.request('ryde-chat-cookie', action) : action();
    const pending = mutationQueue.then(run, run);
    mutationQueue = pending.catch(() => {});
    return pending;
  }
  const invalidationListeners = new Set();
  let channel;
  try { if (root.BroadcastChannel && root.addEventListener) { channel = new root.BroadcastChannel('ryde-chat-invalidation'); channel.unref?.(); } } catch (_) {}
  function invalidate(broadcast = true) {
    for (const listener of invalidationListeners) listener();
    if (broadcast) broadcastInvalidation();
  }
  function broadcastInvalidation() { channel?.postMessage('locked'); }
  if (channel) channel.onmessage = event => { if (event.data === 'locked') invalidate(false); };
  function onInvalidation(listener) { invalidationListeners.add(listener); return () => invalidationListeners.delete(listener); }
  function createClient(fetcher = (...args) => root.fetch(...args), {timeoutMs = 10000, setTimer = setTimeout, clearTimer = clearTimeout} = {}) {
    async function request(path, method = 'GET', body) {
      const controller = new AbortController();
      let timer;
      const work = async () => {
      const response = await fetcher(BASE + path, {method, signal:controller.signal, credentials:'same-origin', cache:'no-store',
        headers:body === undefined ? {} : {'Content-Type':'application/json'}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
      if (!response.ok) {
        const error = new Error(response.status === 404 ? 'Communication Log unavailable or expired. Prepare this Rider case again.' : response.status === 403 ? 'Communication Log locked or belongs to another browser session. Enter the code or prepare this case again.' : 'Communication Log service could not complete the request. Retry or prepare this case again.');
        error.status = response.status; throw error;
      }
      return response.status === 204 ? null : response.json();
      };
      try { return await Promise.race([work(), new Promise((_, reject) => { timer = setTimer(() => {controller.abort(); reject(new Error('Request timed out'));}, timeoutMs); })]); }
      catch (error) { if(error.status)throw error;throw new Error('Communication Log service unavailable or timed out. Retry when the local backend is running. Your report and case are still available.'); }
      finally { clearTimer(timer); }
    }
    const path = handle => '/' + encodeURIComponent(handle);
    return Object.freeze({
      register: payload => transaction(() => request('', 'POST', payload)),
      read: handle => request(path(handle)),
      unlock: (handle, code) => transaction(() => request(path(handle) + '/unlock', 'POST', {code})),
      lock: handle => transaction(() => request(path(handle) + '/lock', 'POST'))
    });
  }
  function redact(result) {
    result.communication_log = [];
    if (result.evidence) result.evidence.log = [];
    return result;
  }
  const client = createClient();
  async function prepare(result, backend = client) {
    // Python case/evidence endpoints already store the real log behind this handle.
    // Never replace a server-created handle by registering an empty browser log.
    if (result.transcript_handle && !result.communication_log?.length && !result.evidence?.log?.length) return redact(result);
    const {rider_id, trip_id, report_id} = result.context;
    // Never upload the original report, media or full evidence.
    const payload = {context:{rider_id, trip_id, report_id}, communication_log:result.communication_log?.length ? result.communication_log : (result.evidence?.log || [])};
    delete result.transcript_handle;
    try {
      const response = await backend.register(payload);
      if (typeof response.handle !== 'string' || !response.handle) throw new Error('Communication Log registration returned no handle. Prepare the case again.');
      result.transcript_handle = response.handle;
      return result;
    } finally { redact(result); }
  }
  function activity(entry) {
    const actors = {'Rider Evidence Agent':'Rider Evidence', 'Rider Policy Agent':'Rider Policy', 'Rider Advocate':'Rider Advocate', Application:'Application'};
    const known = Object.prototype.hasOwnProperty.call(actors, entry.agent);
    const actor = known ? actors[entry.agent] : 'Application';
    let route = 'Recorded activity · local case store';
    if (actor === 'Rider Evidence' && ['evidence_requested', 'evidence_request'].includes(entry.kind)) route = 'Reads Rider-visible records';
    else if (actor === 'Rider Evidence' && ['evidence_returned', 'evidence_response'].includes(entry.kind)) route = 'Returns to local case store';
    else if (actor === 'Rider Policy' && entry.kind === 'policy_retrieved') route = 'Report → draft policy matching → local case store';
    else if (actor === 'Rider Advocate' && entry.kind === 'submission_prepared') route = 'Submission → local case store';
    else if (actor === 'Application' && ['agent_dispatched', 'handoff_recorded'].includes(entry.kind)) route = 'Application coordination · via local case store';
    return {actor, sender: known ? entry.agent : `Recorded activity (${entry.agent || 'unknown actor'})`, route,
      kind: entry.kind || 'recorded_activity', timestamp: entry.timestamp || '', summary: entry.summary || '', references: entry.references || []};
  }
  function messages(log, actor = '') { return log.map(activity).filter(item => !actor || item.actor === actor); }
  const node = (tag, cls, text) => { const element = document.createElement(tag); if (cls) element.className = cls; if (text !== undefined) element.textContent = text; return element; };
  let sequence = 0;
  const panels = new Set(), mounted = new WeakMap();
  function clearAll(error = '') { for (const panel of panels) panel.clear(error); }
  onInvalidation(() => clearAll());
  function mount(container, handle, {caseLabel = '', context, onAccessChange = () => {}, onRecover = () => {}, backend = client} = {}) {
    mounted.get(container)?.dispose();
    const id = `agent-chat-${++sequence}`;
    let filter = '', log = [], generation = 0, unlocked = false, disposed = false, timer;
    function clear(error = '', focus = false) {
      generation++; unlocked = false; log = []; filter = ''; clearTimeout(timer);
      onAccessChange(false);
      if (!disposed) render(error, focus);
    }
    function dispose() { if(disposed)return;clear(); disposed = true; panels.delete(control); if(mounted.get(container)===control)container.replaceChildren(); }
    function validate(data) {
      if (!Array.isArray(data.communication_log) || (context && ['rider_id','trip_id','report_id'].some(key => data.context?.[key] !== context[key]))) throw new Error('The Communication Log does not match this report. Prepare the Rider case again.');
      return data;
    }
    async function readForExport() {
      if (!unlocked || disposed) throw new Error('Unlock the Communication Log before downloading the case.');
      const version = generation;
      try {
        const data = validate(await backend.read(handle));
        if (version !== generation || !unlocked || disposed) throw new Error('Communication Log was locked or replaced. Unlock and retry.');
        return data.communication_log;
      } catch (error) { if (version === generation) {invalidate();clearAll(error.message);} throw error; }
    }
    async function lock() {
      invalidate();clear('', true);
      try { await backend.lock(handle); }
      catch (error) { if (!disposed) clear(`Locked on this page. Server revocation could not be confirmed: ${error.message}`, true); }
    }
    function render(error = '', focus = false) {
      container.replaceChildren(); container.className = 'agent-chat'; container.setAttribute('aria-label', 'Communication Log');
      const header = node('div', 'agent-chat-header');
      const heading = node('div'); heading.append(node('p', 'agent-chat-eyebrow', 'Recorded collaboration'), node('h4', '', 'Communication Log'));
      if (caseLabel) heading.append(node('p', 'agent-chat-context', caseLabel)); header.append(heading); container.append(header);
      container.append(node('p', 'agent-chat-note', 'The local case store coordinates handoffs. Advocates do not chat directly with each other. These are stored public activity summaries.'));
      if (!unlocked) {
        const form = node('form', 'agent-chat-gate');
        const label = node('label', '', 'Communication Log access code'); label.htmlFor = `${id}-code`;
        const input = node('input'); input.id = label.htmlFor; input.type = 'password'; input.autocomplete = 'off'; input.inputMode = 'numeric'; input.setAttribute('aria-describedby', `${id}-error`);
        const submit = node('button', '', 'Unlock'); submit.type = 'submit'; submit.disabled = !handle;
        const alert = node('p', 'agent-chat-error', error); alert.id = `${id}-error`; alert.setAttribute('role', 'alert');
        if (error) input.setAttribute('aria-invalid', 'true');
        form.append(label, input, submit, alert);
        form.onsubmit = async event => {
          event.preventDefault(); const code = input.value; input.value = ''; submit.disabled = true;
          const version = ++generation;
          try {
            await backend.unlock(handle, code);
            if (disposed || version !== generation) return;
            const data = validate(await backend.read(handle));
            if (disposed || version !== generation) return;
            log = data.communication_log; unlocked = true;
            timer = setTimeout(() => {invalidate();clearAll('Communication Log session expired. Enter the code again.');}, Math.max(0, Number(data.expires_in) || 0) * 1000);
            timer?.unref?.(); render('', true); onAccessChange(true);
          } catch (failure) {
            if (!disposed && version === generation) {
              const error=failure.status === 403 ? 'Access denied. Incorrect code or unavailable browser session. Please try again.' : failure.message;
              if(failure.status===403)invalidate();
              clear(error, true);
            }
          }
        };
        container.append(node('p', 'agent-chat-status', 'Locked · Enter the demo access code to view recorded activity.'), form);
        if (!handle || error) { const retry = node('button', '', handle ? 'Retry access' : 'Prepare Communication Log again'); retry.type = 'button'; retry.onclick = () => handle ? clear() : onRecover(); container.append(retry); }
        if (handle && error) { const recover = node('button', '', 'Prepare Rider case again'); recover.type = 'button'; recover.onclick = onRecover; container.append(recover); }
        if (focus) input.focus();
      } else {
        const lockButton = node('button', 'agent-chat-lock', 'Lock'); lockButton.type = 'button'; lockButton.onclick = lock; header.append(lockButton);
        const controls = node('div', 'agent-chat-filter'); const label = node('label', '', 'Filter activity by actor'); label.htmlFor = `${id}-filter`;
        const select = node('select'); select.id = label.htmlFor; select.append(node('option', '', 'All activity')); select.firstChild.value = '';
        for (const actor of new Set(messages(log).map(item => item.actor))) { const option = node('option', '', actor); option.value = actor; select.append(option); }
        select.value = filter;
        const list = node('ol', 'agent-chat-messages'); list.setAttribute('aria-live', 'polite');
        function populate() {
          list.replaceChildren();
          for (const item of messages(log, filter)) {
            const row = node('li', 'agent-chat-message'); const meta = node('div', 'agent-chat-meta');
            meta.append(node('strong', '', item.sender), node('span', 'agent-chat-kind', item.kind));
            const time = node('time', '', item.timestamp || 'Timestamp not recorded'); if (item.timestamp) time.dateTime = item.timestamp;
            row.append(meta, node('p', 'agent-chat-route', item.route), time, node('p', 'agent-chat-summary', item.summary));
            if (item.references.length) row.append(node('p', 'agent-chat-citations', item.references.join(' · ')));
            list.append(row);
          }
          if (!list.childNodes.length) list.append(node('li', 'agent-chat-note', 'No recorded activity.'));
        }
        select.onchange = () => { filter = select.value; populate(); }; controls.append(label, select); container.append(controls, list); populate();
        if (focus) lockButton.focus();
      }
    }
    const control = Object.freeze({clear, dispose, readForExport, lock});
    panels.add(control); mounted.set(container, control); clear(); return control;
  }
  if (root.addEventListener) {
    root.addEventListener('pagehide', () => clearAll());
    root.addEventListener('pageshow', event => { if (event.persisted) clearAll(); });
    root.addEventListener('focus', () => clearAll());
    root.document?.addEventListener?.('visibilitychange', () => { if(root.document.visibilityState === 'visible')clearAll(); });
  }
  const api = Object.freeze({createClient, client, prepare, redact, activity, messages, mount, clearAll, invalidate, broadcastInvalidation, onInvalidation, transaction});
  root.AgentChat = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
