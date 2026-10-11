(function (root) {
  'use strict';
  const data = root.RydeDemo || require('./data.js');
  const evidenceAgent = root.RiderEvidenceAgent || require('./rider-evidence-agent.js');
  const policyAgent = root.RiderPolicyAgent || require('./rider-policy-agent.js');
  const advocate = root.RiderAdvocateAgent || require('./rider-advocate-agent.js');
  const policies = root.WaypointPolicies || require('../shared/policies.js');
  const copy = value => JSON.parse(JSON.stringify(value));
  const supported = ['No-show / cancellation', 'Route deviation'];
  function freeze(value) { if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); } return value; }
  function validateReport(report) {
    if (!report || typeof report !== 'object' || report.reporterRole !== 'Rider' || report.demo !== true || !report.confirmation) throw new Error('Create and confirm a demo Rider report before preparing a case.');
    for (const key of ['id', 'createdAt', 'category', 'summary', 'statement']) {
      if (typeof report[key] !== 'string' || !report[key].trim()) throw new Error(`The report needs a valid ${key}.`);
    }
    if (!report.trip || typeof report.trip.reference !== 'string' || !report.trip.reference.trim()) throw new Error('Select a known demo trip before preparing a Rider case.');
    if (!Array.isArray(report.evidence) || report.evidence.some(item => !item || typeof item !== 'object' || Array.isArray(item))) throw new Error('Report attachment metadata is invalid.');
    if (report.categoryDetails && (typeof report.categoryDetails !== 'object' || Array.isArray(report.categoryDetails))) throw new Error('Report category details are invalid.');
    const request = report.requestedResolution;
    if (request && (typeof request !== 'object' || Array.isArray(request))) throw new Error('Requested resolution is invalid.');
    if (request?.amount !== undefined && (typeof request.amount !== 'number' || !Number.isFinite(request.amount) || request.amount <= 0 || request.currency !== 'SGD')) throw new Error('A requested amount must be positive and use SGD.');
  }
  function resolveRider(report, selectedRider) {
    validateReport(report);
    if (selectedRider) { data.trip(selectedRider, report.trip.reference); return selectedRider; }
    const owners = data.riders().filter(rider => data.trips(rider.id).some(trip => trip.id === report.trip.reference));
    if (owners.length !== 1) throw new Error('This trip is not in the simulated Rider app. Your report can still be downloaded; no trip records were invented.');
    return owners[0].id;
  }
  function run({ report, riderId }) {
    validateReport(report);
    const owner = resolveRider(report, riderId);
    const source = freeze(copy(report));
    const context = { rider_id: owner, trip_id: source.trip.reference, report_id: source.id };
    const log = [];
    const event = (agent, kind, summary, references = []) => log.push({timestamp: new Date().toISOString(), agent, kind, summary, references});
    event('Application', 'intake_validated', 'Confirmed the demo Rider, Trip, and report snapshot.');
    if (!supported.includes(source.category)) {
      event('Application', 'support_routing_required', 'This category is outside the two configured case-building categories. No Advocate Submission was generated.');
      return {schema_version:'local-rider-case-1', status:'support_required', context, original_report:copy(source), communication_log:log,
        message:'This prototype prepares Rider cases for no-show/cancellation and route deviation. This report needs a support or safety review. Nothing has been sent to a reviewer; keep the report JSON.', simulated:true};
    }
    const localStore = {};
    event('Application', 'agent_dispatched', 'Step 3 · Ask the Rider Evidence Agent to gather this report’s trip records.');
    localStore.evidence = freeze(evidenceAgent.collect({riderId:owner, tripId:context.trip_id, report:source}));
    localStore.evidence.log.forEach(entry => event(entry.agent, entry.kind === 'evidence_request' ? 'evidence_requested' : 'evidence_returned', entry.summary, entry.references || []));
    event('Application', 'handoff_recorded', 'Evidence Agent → local case store → Policy Agent: original report, source IDs, and missing-data flags.', localStore.evidence.items.map(item=>item.id));
    event('Application', 'agent_dispatched', 'Step 4 · Ask the Rider Policy Agent for relevant clauses from the shared draft policy version.');
    localStore.policy = freeze(policyAgent.extract(source));
    if (localStore.policy.policy_version !== policies.version || localStore.policy.status !== 'matched') throw new Error('The policy output does not match the case policy source.');
    localStore.policy.matches.forEach(match => {
      const clause = policies.clauses.find(item=>item.id===match.reference && item.role==='Rider');
      if (!clause || clause.text !== match.excerpt) throw new Error('Policy source verification failed.');
    });
    event('Rider Policy Agent', 'policy_retrieved', `Retrieved ${localStore.policy.matches.length} clauses from ${localStore.policy.policy_version}. Matches are guidance, not findings.`, localStore.policy.matches.map(match=>match.reference));
    event('Application', 'rider_snapshot_frozen', 'Preserved an immutable Rider-visible evidence snapshot. A complete shared Case evidence set and Judge review are not implemented.');
    event('Application', 'handoff_recorded', 'Evidence + Policy → local case store → Rider Advocate: complete outputs, report, gaps, and policy limits.');
    const submission = advocate.prepare({report:source, evidence:localStore.evidence, policy:localStore.policy});
    const reviewRequired = /unsafe|threat|harass|danger|violence/i.test([source.summary, source.statement, ...Object.values(source.categoryDetails || {})].join(' '));
    event('Rider Advocate', 'submission_prepared', 'Step 5 · Prepared the Rider’s strongest supported review request, including counter-evidence and missing information.', submission.facts_relied_on);
    if (reviewRequired) event('Application', 'review_signal', 'Possible safety concern in the report wording. Human review is needed; this local demo does not contact support.');
    return copy({schema_version:'local-rider-case-1', id:`LOCAL-${source.id}`, status:'draft', context, simulated:true,
      original_report:source, policy_version:localStore.policy.policy_version, rider_snapshot_version:`${source.id}:rider-snapshot:1`,
      evidence:localStore.evidence, policy:localStore.policy, submission, review_required:reviewRequired, communication_log:log,
      limitations:['Deterministic local prototype; no language model or live Ryde connection.', 'Rider-visible evidence subset only; no Driver Submission, Judge Ruling, or payment action.', 'Draft policies and reported claims do not establish entitlement. Media content is unavailable to these agents.']});
  }
  const api = Object.freeze({run, resolveRider, validateReport});
  root.RiderCasePipeline = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
