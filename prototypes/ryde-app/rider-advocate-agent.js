(function (root) {
  'use strict';
  const copy = value => JSON.parse(JSON.stringify(value));
  function prepare({ report, evidence, policy }) {
    const items = evidence.items;
    const find = source => items.filter(item => item.source === `rider_app.${source}`);
    const refs = source => find(source).map(item => item.id);
    const clauses = policy.matches.map(match => match.reference);
    const reportRefs = refs('report');
    const receipt = find('receipt')[0];
    const location = find('device_location');
    const isNoShow = report.category === 'No-show / cancellation';
    const argumentsForRider = [{
      title: isNoShow ? 'Review the specific no-show charge' : 'Review how the route change was handled',
      text: isNoShow
        ? 'Ask for a review of the reported cancellation or no-show charge against the booking and pickup coordination records. Preserve the Rider’s original account without treating it as a verified fact.'
        : 'The Rider raises a route concern. Ask for a review of the original booking and recorded route discussion, including whether the change was communicated and agreed.',
      evidence_ids: [...reportRefs, ...refs('booking'), ...refs('conversation')],
      policy_ids: clauses.filter(id => [isNoShow ? 'R-02' : 'R-04', 'R-06'].includes(id))
    }];
    if (receipt) argumentsForRider.push({
      title: 'Keep the requested remedy tied to the receipt',
      text: `The simulated receipt records ${receipt.content.currency} ${Number(receipt.content.total).toFixed(2)} in total charges. It supports checking the recorded amount; it does not establish that the charge was unjustified or that the full amount is refundable.`,
      evidence_ids: [receipt.id, ...reportRefs], policy_ids: clauses.filter(id => ['R-02', 'R-03'].includes(id))
    });
    const counterArguments = [];
    const messages = find('conversation').filter(item => item.status === 'available');
    if (messages.some(item => item.content.sender === 'Driver')) counterArguments.push({
      title: 'The Driver’s messages must also be considered',
      text: 'The supplied conversation contains the Driver’s account. Read the complete exchange below, including statements that challenge the Rider. A message is not verified GPS, proof that it was read, or proof that a route change was agreed.',
      evidence_ids: messages.map(item => item.id)
    });
    const gaps = items.filter(item => item.status === 'missing').map(item => ({
      evidence_ids: [item.id], text: item.content.reason || 'This source was not supplied.'
    }));
    if (location.length && location.every(item => item.status === 'missing')) {
      argumentsForRider.push({title: 'Request clarification where location evidence is absent',
        text: 'The Rider’s location cannot be checked from the available app records. Ask that this uncertainty be acknowledged during review; missing GPS does not prove either party’s account.',
        evidence_ids: location.map(item => item.id), policy_ids: []});
    }
    if (!isNoShow) gaps.push({text: 'The app supplies no complete travelled path, optimal route comparison, original fare quote, or verified excess-distance calculation. Two endpoint samples cannot prove a detour or an overcharge.', evidence_ids: refs('device_location')});
    counterArguments.push({title: 'The policies do not promise this outcome',
      text: 'These draft clauses provide review and reporting guidance. They set no numerical no-show waiting threshold or automatic refund entitlement. The requested remedy remains the Rider’s request.', evidence_ids: []});
    const result = {
      author: 'Rider Advocate', claim_restated: report.summary, rider_statement: report.statement,
      requested_outcome: copy(report.requestedResolution || {}),
      facts_relied_on: items.filter(item => item.status === 'available').map(item => item.id),
      arguments: argumentsForRider, counter_arguments: counterArguments, gaps,
      policy_references: clauses,
      conclusion: isNoShow
        ? 'Present the Rider’s request for review of the disputed cancellation charge. The account and receipt justify a focused review request; the available records do not establish who was at fault or guarantee a reversal.'
        : 'Present the Rider’s request for review of the route and any disputed charges. Ask for missing route and consent records before deciding responsibility or calculating a remedy.'
    };
    const ids = new Set(items.map(item => item.id));
    for (const point of [...result.arguments, ...result.counter_arguments, ...result.gaps]) {
      if ((point.evidence_ids || []).some(id => !ids.has(id)) || (point.policy_ids || []).some(id => !clauses.includes(id))) throw new Error('The Rider Submission contains an unresolved citation.');
    }
    return result;
  }
  const api = Object.freeze({ prepare });
  root.RiderAdvocateAgent = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
