(function (root) {
  'use strict';
  const data = root.RydeDemo;
  const key = (rider, trip) => `ryderesolve:rider-report:v1:${rider}:${trip}`;
  function save(riderId, tripId, report) {
    data.trip(riderId, tripId);
    if (!report || report.reporterRole !== 'Rider' || report.trip?.reference !== tripId || report.demo !== true || !report.confirmation) {
      throw new Error('Only a completed demo rider report for this trip can be saved.');
    }
    const serialized = JSON.stringify({ riderId, tripId, report, savedAt: new Date().toISOString() });
    if (serialized.length > 250000) throw new Error('This report is too large for the prototype session store.');
    root.sessionStorage.setItem(key(riderId, tripId), serialized);
  }
  function read(riderId, tripId) {
    data.trip(riderId, tripId);
    const raw = root.sessionStorage.getItem(key(riderId, tripId));
    if (!raw) return null;
    const value = JSON.parse(raw);
    if (value.riderId !== riderId || value.tripId !== tripId || value.report?.reporterRole !== 'Rider' || value.report?.trip?.reference !== tripId || !Array.isArray(value.report.evidence)) {
      throw new Error('Saved report does not match this rider and trip. Clear the saved report and try again.');
    }
    return value.report;
  }
  root.RiderReportStore = Object.freeze({ save, read, remove: (r, t) => { data.trip(r, t); root.sessionStorage.removeItem(key(r, t)); } });
})(window);
