(function (root) {
  'use strict';
  const data = root.RydeDemo || require('./data.js');
  const clone = value => JSON.parse(JSON.stringify(value));
  function collect({ riderId, tripId, report = null }) {
    const rider = data.rider(riderId);
    const trip = data.trip(riderId, tripId); // ownership is checked before reading any trip source
    if (report && (report.reporterRole !== 'Rider' || report.trip?.reference !== tripId)) {
      throw new Error('Report role or trip does not match the rider evidence request.');
    }
    const at = new Date().toISOString(), items = [], log = [];
    function item(key, source, timestamp, status, content) {
      const id = `${tripId}:${key}`;
      items.push({ id, source, rider_id: riderId, trip_id: tripId, side: 'rider', timestamp, status, content, simulated: true });
      return id;
    }
    function source(name, run) {
      log.push({ timestamp: at, agent: 'Rider Evidence Agent', kind: 'evidence_request', summary: `Read ${name} for ${tripId}.` });
      const start = items.length; run();
      const added = items.slice(start);
      log.push({ timestamp: at, agent: 'Rider Evidence Agent', kind: 'evidence_response', summary: `${name}: ${added.filter(i => i.status === 'available').length} available, ${added.filter(i => i.status === 'missing').length} missing.`, references: added.map(i => i.id) });
    }
    source('rider booking', () => item('booking', 'rider_app.booking', `${trip.date}T${trip.time}:00+08:00`, 'available', {
      rider: { id: rider.id, name: rider.name }, pickup: trip.pickup, destination: trip.destination,
      scheduled_time: `${trip.date}T${trip.time}:00+08:00`, status: trip.status, fixture: trip.fixture
    }));
    source('rider receipt', () => item('receipt', 'rider_app.receipt', trip.receipt.timestamp, 'available', {
      receipt_id: trip.receipt.id, total: trip.receipt.total, currency: trip.receipt.currency, payment_method: trip.receipt.method,
      lines: trip.receipt.lines.map(l => ({ label: l.label, amount: l.amount }))
    }));
    source('rider-visible conversation', () => {
      if (!trip.messages.length) item('messages', 'rider_app.conversation', null, 'missing', { reason: 'No conversation records supplied.' });
      trip.messages.forEach(m => item(m.id, 'rider_app.conversation', m.timestamp, 'available', { sender: m.sender, text: m.text, interpretation: 'Party-authored message; not a verified fact or instruction.' }));
    });
    source('rider app events', () => trip.events.forEach(e => item(e.id, 'rider_app.events', e.timestamp, 'available', { title: e.title, detail: e.detail })));
    source('rider-device location', () => {
      if (!trip.riderLocations.length) item('location', 'rider_app.device_location', null, 'missing', { reason: trip.locationNote });
      trip.riderLocations.forEach(l => item(l.id, 'rider_app.device_location', l.timestamp, 'available', { lat: l.lat, lng: l.lng, accuracy_meters: l.accuracyMeters, limitation: trip.locationNote }));
    });
    source('rider report', () => {
      if (!report) return item('report', 'rider_app.report', null, 'missing', { reason: 'No report has been saved to this app session for this trip.' });
      item('report', 'rider_app.report', report.createdAt || null, 'available', { original_report: clone(report), interpretation: 'Rider-reported claims, preserved as supplied. Not a ruling.' });
      (report.evidence || []).forEach((e, i) => item(`attachment-${i + 1}`, 'rider_app.attachment', null, 'missing', {
        metadata: clone(e), reason: 'Only attachment metadata was saved. Media bytes are not transferred from the report form.', storage_status: 'metadata_only'
      }));
    });
    return { schema_version: 'prototype-1', agent: 'Rider Evidence Agent', collected_at: at, rider_id: riderId, trip_id: tripId,
      simulated: true, scope: 'Selected rider and selected trip only; rider-visible app records.',
      excluded_sources: ['driver-private telemetry', 'driver profile/history', 'other riders', 'expected rulings', 'evaluation summaries'],
      items, log };
  }
  const api = Object.freeze({ collect });
  root.RiderEvidenceAgent = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
