(function (root) {
  'use strict';
  const riders = [
    { id: 'R-7823', name: 'Michael Wong', initials: 'MW' },
    { id: 'R-DEMO-02', name: 'Aisha Tan', initials: 'AT' }
  ];
  const trips = [
    {
      id: 'TRIP-2026-09945', riderId: 'R-7823', date: '2026-09-13', time: '08:45',
      pickup: 'Tiong Bahru Plaza', destination: 'VivoCity', status: 'Cancelled', service: 'RydeX · simulated',
      category: 'No-show / cancellation', fixture: 'DISP-002 · rider-visible subset',
      receipt: { id: 'RECEIPT-09945', currency: 'SGD', total: 5, method: 'E-wallet', timestamp: '2026-09-13T08:51:00+08:00', lines: [{ label: 'Cancellation fee', amount: 5 }] },
      messages: [
        { id: 'MSG-945-1', timestamp: '2026-09-13T08:43:00+08:00', sender: 'Driver', text: "I've arrived at the pickup point, I'm at the lobby area." },
        { id: 'MSG-945-2', timestamp: '2026-09-13T08:45:20+08:00', sender: 'Driver', text: "I'm waiting at the lobby area, white Honda HR-V plate SGP 4521 M." },
        { id: 'MSG-945-3', timestamp: '2026-09-13T08:49:30+08:00', sender: 'Driver', text: "Hi, are you coming down? I've been waiting a while." },
        { id: 'MSG-945-4', timestamp: '2026-09-13T08:50:45+08:00', sender: 'Driver', text: "Please let me know, otherwise I'll have to cancel the trip." }
      ],
      events: [
        { id: 'EV-945-1', timestamp: '2026-09-13T08:30:00+08:00', title: 'Booking confirmed', detail: 'Scheduled pickup at 08:45.' },
        { id: 'EV-945-2', timestamp: '2026-09-13T08:43:05+08:00', title: 'Arrival notification sent', detail: 'Your driver has arrived. Delivery/read status is not supplied.' },
        { id: 'EV-945-3', timestamp: '2026-09-13T08:51:00+08:00', title: 'Trip cancelled', detail: 'No-show cancellation fee of SGD 5.00 applied.' }
      ],
      riderLocations: [], locationNote: 'DISP-002 supplies driver telemetry, not rider-device location. No rider GPS record is available.'
    },
    {
      id: 'TRIP-DEMO-ROUTE-01', riderId: 'R-7823', date: '2026-09-12', time: '18:10',
      pickup: 'Bugis Junction', destination: 'Marina Bay Sands', status: 'Completed', service: 'RydeX · simulated',
      category: 'Route deviation', fixture: 'Invented route example · not DISP-002',
      receipt: { id: 'RECEIPT-ROUTE-01', currency: 'SGD', total: 18.8, method: 'E-wallet', timestamp: '2026-09-12T18:39:00+08:00', lines: [{ label: 'Trip fare', amount: 16.8 }, { label: 'Booking fee', amount: 2 }] },
      messages: [
        { id: 'MSG-R1-1', timestamp: '2026-09-12T18:17:00+08:00', sender: 'Rider', text: 'Are we taking a different route? The app showed a shorter trip.' },
        { id: 'MSG-R1-2', timestamp: '2026-09-12T18:18:00+08:00', sender: 'Driver', text: 'There is traffic ahead. I am taking another road.' }
      ],
      events: [
        { id: 'EV-R1-1', timestamp: '2026-09-12T18:10:00+08:00', title: 'Booking confirmed', detail: 'Bugis Junction to Marina Bay Sands.' },
        { id: 'EV-R1-2', timestamp: '2026-09-12T18:39:00+08:00', title: 'Trip completed', detail: 'Receipt available in your account.' }
      ],
      riderLocations: [
        { id: 'LOC-R1-1', timestamp: '2026-09-12T18:10:00+08:00', lat: 1.299, lng: 103.855, accuracyMeters: 25 },
        { id: 'LOC-R1-2', timestamp: '2026-09-12T18:39:00+08:00', lat: 1.283, lng: 103.86, accuracyMeters: 30 }
      ], locationNote: 'Two invented rider-device samples. These do not establish the route taken between endpoints.'
    },
    {
      id: 'TRIP-DEMO-AISHA-01', riderId: 'R-DEMO-02', date: '2026-09-14', time: '10:00',
      pickup: 'Orchard Central', destination: 'Singapore Botanic Gardens', status: 'Completed', service: 'RydeX · simulated',
      category: 'Other', fixture: 'Invented second account · scope demonstration',
      receipt: { id: 'RECEIPT-A1', currency: 'SGD', total: 12.5, method: 'E-wallet', timestamp: '2026-09-14T10:18:00+08:00', lines: [{ label: 'Trip fare', amount: 10.5 }, { label: 'Booking fee', amount: 2 }] },
      messages: [], events: [{ id: 'EV-A1-1', timestamp: '2026-09-14T10:18:00+08:00', title: 'Trip completed', detail: 'Receipt available in your account.' }],
      riderLocations: [], locationNote: 'No rider-device location samples in this example.'
    }
  ];
  const clone = value => JSON.parse(JSON.stringify(value));
  function rider(id) { const value = riders.find(r => r.id === id); if (!value) throw new Error('Unknown demo rider.'); return clone(value); }
  function trip(riderId, tripId) {
    rider(riderId);
    const value = trips.find(t => t.id === tripId && t.riderId === riderId);
    if (!value) throw new Error('This trip is not available to the selected rider.');
    return clone(value);
  }
  const api = { riders: () => clone(riders), rider, trips: id => { rider(id); return clone(trips.filter(t => t.riderId === id)); }, trip };
  root.RydeDemo = Object.freeze(api);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
