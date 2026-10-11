(function (root) {
  'use strict';
  const data = root.RydeDemo || require('./data.js');
  function create(storage) {
    const key = (rider, trip) => `waypoint:rider-case:v1:${rider}:${trip}`;
    function check(rider, trip, report, result) {
      data.trip(rider, trip);
      if (!result || result.schema_version !== 'local-rider-case-1' || !['draft','support_required'].includes(result.status) || result.context?.rider_id !== rider || result.context?.trip_id !== trip || result.context?.report_id !== report?.id || report?.reporterRole !== 'Rider' || report?.trip?.reference !== trip || JSON.stringify(result.original_report) !== JSON.stringify(report)) throw new Error('The stored Rider case does not match the current report snapshot. Prepare it again.');
    }
    return Object.freeze({
      save(rider, trip, report, result) {
        check(rider, trip, report, result);
        const serialized = JSON.stringify(result);
        if (serialized.length > 750000) throw new Error('The Rider case is too large for this local session. Download it instead.');
        storage.setItem(key(rider, trip), serialized);
      },
      read(rider, trip, report) {
        data.trip(rider, trip);
        const raw = storage.getItem(key(rider, trip));
        if (!raw) return null;
        const result = JSON.parse(raw);
        check(rider, trip, report, result);
        return result;
      },
      remove(rider, trip) { data.trip(rider, trip); storage.removeItem(key(rider, trip)); }
    });
  }
  // Access to sessionStorage itself may be denied; expose the error at the action.
  root.RiderCaseStore = Object.freeze({
    save: (...args) => create(root.sessionStorage).save(...args),
    read: (...args) => create(root.sessionStorage).read(...args),
    remove: (...args) => create(root.sessionStorage).remove(...args)
  });
  if (typeof module !== 'undefined' && module.exports) module.exports = {create};
})(typeof window !== 'undefined' ? window : globalThis);
