(function (root) {
  'use strict';
  const policies = root.WaypointPolicies || (typeof require === 'function' ? require('../shared/policies.js') : null);
  const categoryRefs = {
    'No-show / cancellation': ['R-02'],
    'Route deviation': ['R-04'],
    'Fare / payment': ['R-03'],
    'Safety / conduct': ['R-05'],
    'Damage / mess': ['R-07'],
    'Lost item': ['R-08'],
    Other: ['R-09']
  };
  function retrieve(report, limit) {
    if (!report || typeof report !== 'object') throw new TypeError('A report object is required.');
    if (report.reporterRole !== 'Rider') return {
      schema_version: 'prototype-1', agent: 'Rider Policy Agent', policy_version: policies.version,
      status: 'not_applicable', scope: 'Rider reports only.', matches: [],
      message: 'This rider-only agent does not extract policy references for driver reports.'
    };

    const text = [report.category, report.summary, report.statement,
      ...Object.values(report.categoryDetails || {}), report.incident?.location, ...(report.evidence || []).map(item => item.caption)]
      .filter(v => typeof v === 'string').join(' ').toLocaleLowerCase();
    const reasons = new Map();
    const add = (id, reason) => { const list = reasons.get(id) || []; if (!list.includes(reason)) list.push(reason); reasons.set(id, list); };
    (categoryRefs[report.category] || ['R-09']).forEach(id => add(id, `Issue category: ${report.category || 'not provided'}`));
    for (const clause of policies.clauses.filter(c => c.role === 'Rider')) {
      for (const keyword of clause.keywords) {
        const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        if (keyword.length > 2 && new RegExp(`\\b${escaped}\\b`, 'i').test(text)) add(clause.id, `Report wording relates to “${keyword}”`);
      }
    }
    add('R-06', 'General report-handling guidance');
    const rank = id => reasons.get(id)?.length || 0;
    const matches = [...reasons.keys()].map(id => {
      const clause = policies.clauses.find(c => c.id === id);
      return { reference: clause.id, title: clause.title, category: clause.category, excerpt: clause.text, relevance_signals: reasons.get(id) };
    }).sort((a, b) => rank(b.reference) - rank(a.reference) || a.reference.localeCompare(b.reference)).slice(0, limit);
    return {
      schema_version: 'prototype-1', agent: 'Rider Policy Agent', policy_version: policies.version,
      status: 'matched', scope: 'Rider report only; deterministic category and keyword matching.',
      matches,
      limitations: ['References are informational draft guidance, not approved contract terms or legal advice.', 'A match does not verify a reported event, determine responsibility, or recommend a refund, compensation, or other outcome.', 'This browser prototype processes the report in-page and does not send it to a policy service.']
    };
  }
  const api = Object.freeze({ match: report => retrieve(report, 5), extract: report => retrieve(report, Infinity) });
  root.RiderPolicyAgent = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
