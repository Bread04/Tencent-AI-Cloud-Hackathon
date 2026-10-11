(function (root) {
  'use strict';
  const riders = [
    { id: 'R-7823', name: 'Michael Wong', initials: 'MW' },
    { id: 'R-DEMO-02', name: 'Aisha Tan', initials: 'AT' },
    { id: 'R-7824', name: 'Demo rider R-7824', initials: 'R3' },
    { id: 'R-7825', name: 'Demo rider R-7825', initials: 'R4' }
  ];
  const trips = [
    {
      id: 'TRIP-2026-09945', riderId: 'R-7823', date: '2026-09-13', time: '08:45',
      pickup: 'Tiong Bahru Plaza', destination: 'VivoCity', status: 'Cancelled', service: 'RydeX · simulated',
      category: 'No-show / cancellation', fixture: 'DISP-002 · rider-visible subset',
      sampleReport: {"id": "DISP-002", "summary": "Dispute of SGD 5.00 no-show cancellation fee", "statement": "I was at the pickup point at Tiong Bahru Plaza on time but the driver never showed up. I waited 10 minutes at the lobby and couldn't find the car. The app charged me a $5.00 cancellation fee for a 'no-show' which is completely unfair — I was there, the driver was not. I want the charge reversed immediately.", "incidentTime": "", "categoryDetails": {"situation": "A no-show / cancellation fee was charged", "waiting": "10"}},
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
      "id": "TRIP-2026-09946",
      "riderId": "R-7824",
      "date": "2026-09-14",
      "time": "10:00",
      "pickup": "Bugis Junction pickup bay",
      "destination": "Suntec City",
      "status": "Cancelled",
      "service": "RydeX · simulated",
      "category": "No-show / cancellation",
      "fixture": "DISP-003 · rider-visible subset",
      "sampleReport": {
        "id": "DISP-003",
        "summary": "Dispute of SGD 5.00 no-show cancellation fee",
        "statement": "My driver arrived at the Bugis Junction pickup point at 10:00. I messaged at 10:01 that I was coming to the pickup bay, but the driver cancelled at 10:04 and I was charged $5.00 for a no-show. The app's five-minute free wait had not ended, and the eight-minute no-show threshold had not been reached. Please reverse the charge.",
        "incidentTime": "2026-09-14T10:04",
        "categoryDetails": {
          "situation": "A no-show / cancellation fee was charged",
            "contact": "In-app message"
        }
      },
      "receipt": {
        "id": "RECEIPT-09946",
        "currency": "SGD",
        "total": 5.0,
        "method": "Simulated payment",
        "timestamp": "2026-09-14T10:04:00+08:00",
        "lines": [
          {
            "label": "Cancellation fee",
            "amount": 5.0
          }
        ]
      },
      "messages": [
        {
          "id": "MSG-003-1",
          "timestamp": "2026-09-14T10:00:10+08:00",
          "sender": "Driver",
          "text": "I am at the booked pickup bay."
        },
        {
          "id": "MSG-003-2",
          "timestamp": "2026-09-14T10:01:00+08:00",
          "sender": "Rider",
          "text": "I am coming to the pickup bay. Please wait."
        },
        {
          "id": "MSG-003-3",
          "timestamp": "2026-09-14T10:03:30+08:00",
          "sender": "Driver",
          "text": "I cannot see you yet. I am going to cancel."
        }
      ],
      "events": [
        {
          "id": "EV-003-1",
          "timestamp": "2026-09-14T09:45:00+08:00",
          "title": "Booking confirmed",
          "detail": "Rider R-7824 booked TRIP-2026-09946 from Bugis Junction pickup bay to Suntec City. Scheduled pickup 10:00."
        },
        {
          "id": "EV-003-2",
          "timestamp": "2026-09-14T10:00:00+08:00",
          "title": "Arrival notification",
          "detail": "The app recorded driver arrival. This notification does not independently verify physical presence."
        },
        {
          "id": "EV-003-3",
          "timestamp": "2026-09-14T10:00:00+08:00",
          "title": "Wait timer started",
          "detail": "Five-minute free wait ends at 10:05. Eight-minute no-show threshold ends at 10:08."
        },
        {
          "id": "EV-003-4",
          "timestamp": "2026-09-14T10:04:00+08:00",
          "title": "Trip cancelled",
          "detail": "Driver cancelled the trip with reason rider_no_show."
        },
        {
          "id": "EV-003-5",
          "timestamp": "2026-09-14T10:04:00+08:00",
          "title": "Cancellation fee charged",
          "detail": "$5.00 no-show cancellation fee charged to the rider."
        }
      ],
      "riderLocations": [],
      "locationNote": "DISP-003 contains no rider-device location records. Driver location must not be treated as rider GPS."
    },
    {
      "id": "TRIP-2026-09947",
      "riderId": "R-7825",
      "date": "2026-09-15",
      "time": "09:00",
      "pickup": "Tiong Bahru Plaza pickup bay",
      "destination": "VivoCity",
      "status": "Cancelled",
      "service": "RydeX · simulated",
      "category": "No-show / cancellation",
      "fixture": "DISP-004 · rider-visible subset",
      "sampleReport": {
        "id": "DISP-004",
        "summary": "Dispute of SGD 5.00 no-show cancellation fee",
        "statement": "I went to the booked pickup bay at Tiong Bahru Plaza but could not find the car. At 09:03 I messaged the driver, who said they were still waiting. I called at 09:05 but we did not connect. At 09:08 the trip was cancelled and I was charged $5.00. I believe the driver had left and want the fee reversed.",
        "incidentTime": "2026-09-15T09:08",
        "categoryDetails": {
          "situation": "A no-show / cancellation fee was charged",
            "contact": "Message and call"
        }
      },
      "receipt": {
        "id": "RECEIPT-09947",
        "currency": "SGD",
        "total": 5.0,
        "method": "Simulated payment",
        "timestamp": "2026-09-15T09:08:00+08:00",
        "lines": [
          {
            "label": "Cancellation fee",
            "amount": 5.0
          }
        ]
      },
      "messages": [
        {
          "id": "MSG-004-1",
          "timestamp": "2026-09-15T09:00:10+08:00",
          "sender": "Driver",
          "text": "I have arrived at the pickup bay."
        },
        {
          "id": "MSG-004-2",
          "timestamp": "2026-09-15T09:03:00+08:00",
          "sender": "Rider",
          "text": "I am at the booked bay but cannot see your car. Have you left?"
        },
        {
          "id": "MSG-004-3",
          "timestamp": "2026-09-15T09:03:30+08:00",
          "sender": "Driver",
          "text": "I am still at the pickup bay. My app location is not updating."
        },
        {
          "id": "MSG-004-4",
          "timestamp": "2026-09-15T09:04:00+08:00",
          "sender": "Driver",
          "type": "call",
        "text": "In-app call to rider rang for 20 seconds; no connection established."
        },
        {
          "id": "MSG-004-5",
          "timestamp": "2026-09-15T09:05:00+08:00",
          "sender": "Rider",
          "type": "call",
        "text": "In-app call to driver rang for 20 seconds; no connection established."
        },
        {
          "id": "MSG-004-6",
          "timestamp": "2026-09-15T09:06:00+08:00",
          "sender": "Rider",
          "text": "I still cannot find you. Please tell me exactly where you are."
        },
        {
          "id": "MSG-004-7",
          "timestamp": "2026-09-15T09:07:00+08:00",
          "sender": "Driver",
          "text": "I am waiting at the bay and will cancel when the timer reaches eight minutes."
        }
      ],
      "events": [
        {
          "id": "EV-004-1",
          "timestamp": "2026-09-15T08:45:00+08:00",
          "title": "Booking confirmed",
          "detail": "Rider R-7825 booked TRIP-2026-09947 from Tiong Bahru Plaza pickup bay to VivoCity. Scheduled pickup 09:00."
        },
        {
          "id": "EV-004-2",
          "timestamp": "2026-09-15T09:00:00+08:00",
          "title": "Arrival notification",
          "detail": "The app recorded driver arrival. This notification does not independently verify physical presence."
        },
        {
          "id": "EV-004-3",
          "timestamp": "2026-09-15T09:00:00+08:00",
          "title": "Wait timer started",
          "detail": "Five-minute free wait ends at 09:05. Eight-minute no-show threshold ends at 09:08."
        },
        {
          "id": "EV-004-4",
          "timestamp": "2026-09-15T09:05:00+08:00",
          "title": "Free wait elapsed",
          "detail": "Five minutes elapsed since arrival. Timer does not verify the driver's current position."
        },
        {
          "id": "EV-004-5",
          "timestamp": "2026-09-15T09:08:00+08:00",
          "title": "Trip cancelled",
          "detail": "Driver cancelled the trip with reason rider_no_show."
        },
        {
          "id": "EV-004-6",
          "timestamp": "2026-09-15T09:08:00+08:00",
          "title": "Cancellation fee charged",
          "detail": "$5.00 no-show cancellation fee charged to the rider."
        }
      ],
      "riderLocations": [],
      "locationNote": "DISP-004 contains no rider-device location records. Driver location must not be treated as rider GPS."
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
  function sampleReports() { return clone(trips.filter(t => t.sampleReport).map(t => ({...t.sampleReport, riderId:t.riderId, tripId:t.id, date:t.date, time:t.time, pickup:t.pickup, destination:t.destination, amount:t.receipt.total, currency:t.receipt.currency}))); }
  const api = { sampleReports, riders: () => clone(riders), rider, trips: id => { rider(id); return clone(trips.filter(t => t.riderId === id)); }, trip };
  root.RydeDemo = Object.freeze(api);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
