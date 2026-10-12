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
  // Ticket 06 public projections (generated from simulated source cases).
  trips.push(...[
  {
    "id": "TRIP-2026-ROUTE-008",
    "riderId": "R-7823",
    "date": "2026-09-16",
    "time": "14:00",
    "pickup": "Bugis Junction",
    "destination": "Marina Bay Sands",
    "status": "Completed",
    "service": "RydeX \u00b7 simulated",
    "category": "Route deviation",
    "fixture": "DISP-008 \u00b7 curated public source projection",
    "sampleReport": {
      "id": "DISP-008",
      "category": "Route deviation",
      "summary": "Review the route and full paid fare",
      "statement": "The trip went via Lavender MRT and stopped for three minutes. I did not ask for that detour. Please refund the full fare.",
      "incidentTime": "2026-09-16T14:00",
      "categoryDetails": {
        "route": "Bugis Junction to Marina Bay Sands",
        "deviation": "Via Lavender MRT with a stop",
        "agreement": "No"
      }
    },
    "receipt": {
      "id": "RECEIPT-008",
      "currency": "SGD",
      "total": 15.08,
      "method": "E-wallet",
      "timestamp": "2026-09-16T14:20:00+08:00",
      "lines": [
        {
          "label": "Base fare (surge \u00d71.20)",
          "amount": 3.6
        },
        {
          "label": "Distance fare (surge \u00d71.20)",
          "amount": 5.68
        },
        {
          "label": "Time fare (surge \u00d71.20)",
          "amount": 6.0
        },
        {
          "label": "Booking fee",
          "amount": 0.8
        },
        {
          "label": "Tolls",
          "amount": 1.0
        },
        {
          "label": "Promotion",
          "amount": -2.0
        }
      ]
    },
    "messages": [
      {
        "id": "MSG-008-1",
        "timestamp": "2026-09-16T14:09:00+08:00",
        "sender": "Rider",
        "text": "Why are we near Lavender MRT? I did not request this detour."
      },
      {
        "id": "MSG-008-2",
        "timestamp": "2026-09-16T14:10:00+08:00",
        "sender": "Driver",
        "text": "I missed the turn and stopped to check the route. Sorry about the extra distance."
      }
    ],
    "events": [
      {
        "id": "APP-008-1",
        "timestamp": "2026-09-16T14:20:00+08:00",
        "title": "Trip completed",
        "detail": "Simulated trip completed. Vehicle GPS is supplied separately; no Rider device GPS was recorded."
      }
    ],
    "riderLocations": [],
    "locationNote": "No Rider device GPS was recorded. Shared simulated vehicle GPS is labelled separately.",
    "routeRecord": {
      "trip": {
        "trip_id": "TRIP-2026-ROUTE-008",
        "rider_id": "R-7823",
        "driver_id": "D-ROUTE-8",
        "pickup_location": {
          "name": "Bugis Junction",
          "lat": 1.299,
          "lng": 103.855
        },
        "dropoff_location": {
          "name": "Marina Bay Sands",
          "lat": 1.283,
          "lng": 103.86
        },
        "scheduled_time": "2026-09-16T14:00:00+08:00",
        "started_at": "2026-09-16T14:00:00+08:00",
        "completed_at": "2026-09-16T14:20:00+08:00",
        "currency": "SGD",
        "paid_net": "15.08"
      },
      "gps_telemetry": [
        {
          "timestamp": "2026-09-16T14:00:00+08:00",
          "lat": 1.299,
          "lng": 103.855
        },
        {
          "timestamp": "2026-09-16T14:01:00+08:00",
          "lat": 1.3006,
          "lng": 103.8566
        },
        {
          "timestamp": "2026-09-16T14:02:00+08:00",
          "lat": 1.3022,
          "lng": 103.8582
        },
        {
          "timestamp": "2026-09-16T14:03:00+08:00",
          "lat": 1.3038,
          "lng": 103.8598
        },
        {
          "timestamp": "2026-09-16T14:04:00+08:00",
          "lat": 1.3054,
          "lng": 103.8614
        },
        {
          "timestamp": "2026-09-16T14:05:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-16T14:06:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-16T14:07:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-16T14:08:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-16T14:09:00+08:00",
          "lat": 1.305,
          "lng": 103.86275
        },
        {
          "timestamp": "2026-09-16T14:10:00+08:00",
          "lat": 1.303,
          "lng": 103.8625
        },
        {
          "timestamp": "2026-09-16T14:11:00+08:00",
          "lat": 1.301,
          "lng": 103.86225
        },
        {
          "timestamp": "2026-09-16T14:12:00+08:00",
          "lat": 1.299,
          "lng": 103.862
        },
        {
          "timestamp": "2026-09-16T14:13:00+08:00",
          "lat": 1.297,
          "lng": 103.86175
        },
        {
          "timestamp": "2026-09-16T14:14:00+08:00",
          "lat": 1.295,
          "lng": 103.8615
        },
        {
          "timestamp": "2026-09-16T14:15:00+08:00",
          "lat": 1.293,
          "lng": 103.86125
        },
        {
          "timestamp": "2026-09-16T14:16:00+08:00",
          "lat": 1.291,
          "lng": 103.861
        },
        {
          "timestamp": "2026-09-16T14:17:00+08:00",
          "lat": 1.289,
          "lng": 103.86075
        },
        {
          "timestamp": "2026-09-16T14:18:00+08:00",
          "lat": 1.287,
          "lng": 103.8605
        },
        {
          "timestamp": "2026-09-16T14:19:00+08:00",
          "lat": 1.285,
          "lng": 103.86025
        },
        {
          "timestamp": "2026-09-16T14:20:00+08:00",
          "lat": 1.283,
          "lng": 103.86
        }
      ],
      "route_baseline": {
        "source_id": "BASELINE-008",
        "simulated": true,
        "expected_minutes": "12.00",
        "points": [
          {
            "lat": 1.299,
            "lng": 103.855
          },
          {
            "lat": 1.291,
            "lng": 103.858
          },
          {
            "lat": 1.283,
            "lng": 103.86
          }
        ]
      },
      "route_landmarks": [
        {
          "id": "LANDMARK-LAVENDER-MRT",
          "name": "Lavender MRT",
          "lat": 1.307,
          "lng": 103.863
        }
      ],
      "tariff": {
        "base": "3.00",
        "km_rate": "1.20",
        "minute_rate": "0.25",
        "surge": "1.20",
        "booking": "0.80",
        "tolls": "1.00",
        "promo": "2.00"
      },
      "receipt": {
        "receipt_id": "RECEIPT-008",
        "trip_id": "TRIP-2026-ROUTE-008",
        "paid_net": "15.08",
        "currency": "SGD",
        "timestamp": "2026-09-16T14:20:00+08:00"
      }
    }
  },
  {
    "id": "TRIP-2026-ROUTE-009",
    "riderId": "R-7823",
    "date": "2026-09-17",
    "time": "14:00",
    "pickup": "Bugis Junction",
    "destination": "Marina Bay Sands",
    "status": "Completed",
    "service": "RydeX \u00b7 simulated",
    "category": "Route deviation",
    "fixture": "DISP-009 \u00b7 curated public source projection",
    "sampleReport": {
      "id": "DISP-009",
      "category": "Route deviation",
      "summary": "Review the route and full paid fare",
      "statement": "The trip was longer than the app baseline and cost more. Please refund the full fare.",
      "incidentTime": "2026-09-17T14:00",
      "categoryDetails": {
        "route": "Bugis Junction to Marina Bay Sands",
        "deviation": "Via Lavender MRT with a stop",
        "agreement": "Yes"
      }
    },
    "receipt": {
      "id": "RECEIPT-009",
      "currency": "SGD",
      "total": 15.08,
      "method": "E-wallet",
      "timestamp": "2026-09-17T14:20:00+08:00",
      "lines": [
        {
          "label": "Base fare (surge \u00d71.20)",
          "amount": 3.6
        },
        {
          "label": "Distance fare (surge \u00d71.20)",
          "amount": 5.68
        },
        {
          "label": "Time fare (surge \u00d71.20)",
          "amount": 6.0
        },
        {
          "label": "Booking fee",
          "amount": 0.8
        },
        {
          "label": "Tolls",
          "amount": 1.0
        },
        {
          "label": "Promotion",
          "amount": -2.0
        }
      ]
    },
    "messages": [
      {
        "id": "MSG-009-1",
        "timestamp": "2026-09-17T13:57:00+08:00",
        "sender": "Rider",
        "text": "Please detour via Lavender MRT and stop there for three minutes so I can collect my bag, then continue to Marina Bay Sands."
      },
      {
        "id": "MSG-009-2",
        "timestamp": "2026-09-17T13:58:00+08:00",
        "sender": "Driver",
        "text": "Yes, I can take that detour and stop for three minutes. The fare may increase."
      },
      {
        "id": "MSG-009-3",
        "timestamp": "2026-09-17T13:59:00+08:00",
        "sender": "Rider",
        "text": "Understood, please go ahead."
      }
    ],
    "events": [
      {
        "id": "APP-009-1",
        "timestamp": "2026-09-17T14:20:00+08:00",
        "title": "Trip completed",
        "detail": "Simulated trip completed. Vehicle GPS is supplied separately; no Rider device GPS was recorded."
      }
    ],
    "riderLocations": [],
    "locationNote": "No Rider device GPS was recorded. Shared simulated vehicle GPS is labelled separately.",
    "routeRecord": {
      "trip": {
        "trip_id": "TRIP-2026-ROUTE-009",
        "rider_id": "R-7823",
        "driver_id": "D-ROUTE-9",
        "pickup_location": {
          "name": "Bugis Junction",
          "lat": 1.299,
          "lng": 103.855
        },
        "dropoff_location": {
          "name": "Marina Bay Sands",
          "lat": 1.283,
          "lng": 103.86
        },
        "scheduled_time": "2026-09-17T14:00:00+08:00",
        "started_at": "2026-09-17T14:00:00+08:00",
        "completed_at": "2026-09-17T14:20:00+08:00",
        "currency": "SGD",
        "paid_net": "15.08"
      },
      "gps_telemetry": [
        {
          "timestamp": "2026-09-17T14:00:00+08:00",
          "lat": 1.299,
          "lng": 103.855
        },
        {
          "timestamp": "2026-09-17T14:01:00+08:00",
          "lat": 1.3006,
          "lng": 103.8566
        },
        {
          "timestamp": "2026-09-17T14:02:00+08:00",
          "lat": 1.3022,
          "lng": 103.8582
        },
        {
          "timestamp": "2026-09-17T14:03:00+08:00",
          "lat": 1.3038,
          "lng": 103.8598
        },
        {
          "timestamp": "2026-09-17T14:04:00+08:00",
          "lat": 1.3054,
          "lng": 103.8614
        },
        {
          "timestamp": "2026-09-17T14:05:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-17T14:06:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-17T14:07:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-17T14:08:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-17T14:09:00+08:00",
          "lat": 1.305,
          "lng": 103.86275
        },
        {
          "timestamp": "2026-09-17T14:10:00+08:00",
          "lat": 1.303,
          "lng": 103.8625
        },
        {
          "timestamp": "2026-09-17T14:11:00+08:00",
          "lat": 1.301,
          "lng": 103.86225
        },
        {
          "timestamp": "2026-09-17T14:12:00+08:00",
          "lat": 1.299,
          "lng": 103.862
        },
        {
          "timestamp": "2026-09-17T14:13:00+08:00",
          "lat": 1.297,
          "lng": 103.86175
        },
        {
          "timestamp": "2026-09-17T14:14:00+08:00",
          "lat": 1.295,
          "lng": 103.8615
        },
        {
          "timestamp": "2026-09-17T14:15:00+08:00",
          "lat": 1.293,
          "lng": 103.86125
        },
        {
          "timestamp": "2026-09-17T14:16:00+08:00",
          "lat": 1.291,
          "lng": 103.861
        },
        {
          "timestamp": "2026-09-17T14:17:00+08:00",
          "lat": 1.289,
          "lng": 103.86075
        },
        {
          "timestamp": "2026-09-17T14:18:00+08:00",
          "lat": 1.287,
          "lng": 103.8605
        },
        {
          "timestamp": "2026-09-17T14:19:00+08:00",
          "lat": 1.285,
          "lng": 103.86025
        },
        {
          "timestamp": "2026-09-17T14:20:00+08:00",
          "lat": 1.283,
          "lng": 103.86
        }
      ],
      "route_baseline": {
        "source_id": "BASELINE-009",
        "simulated": true,
        "expected_minutes": "12.00",
        "points": [
          {
            "lat": 1.299,
            "lng": 103.855
          },
          {
            "lat": 1.291,
            "lng": 103.858
          },
          {
            "lat": 1.283,
            "lng": 103.86
          }
        ]
      },
      "route_landmarks": [
        {
          "id": "LANDMARK-LAVENDER-MRT",
          "name": "Lavender MRT",
          "lat": 1.307,
          "lng": 103.863
        }
      ],
      "tariff": {
        "base": "3.00",
        "km_rate": "1.20",
        "minute_rate": "0.25",
        "surge": "1.20",
        "booking": "0.80",
        "tolls": "1.00",
        "promo": "2.00"
      },
      "receipt": {
        "receipt_id": "RECEIPT-009",
        "trip_id": "TRIP-2026-ROUTE-009",
        "paid_net": "15.08",
        "currency": "SGD",
        "timestamp": "2026-09-17T14:20:00+08:00"
      }
    }
  },
  {
    "id": "TRIP-2026-ROUTE-010",
    "riderId": "R-7823",
    "date": "2026-09-18",
    "time": "14:00",
    "pickup": "Bugis Junction",
    "destination": "Marina Bay Sands",
    "status": "Completed",
    "service": "RydeX \u00b7 simulated",
    "category": "Route deviation",
    "fixture": "DISP-010 \u00b7 curated public source projection",
    "sampleReport": {
      "id": "DISP-010",
      "category": "Route deviation",
      "summary": "Review the route and full paid fare",
      "statement": "The Driver took a longer route via Lavender MRT and stopped. I remember discussing the route but I am not sure we agreed to that detour. Please review the full fare.",
      "incidentTime": "2026-09-18T14:00",
      "categoryDetails": {
        "route": "Bugis Junction to Marina Bay Sands",
        "deviation": "Via Lavender MRT with a stop",
        "agreement": "Not sure"
      }
    },
    "receipt": {
      "id": "RECEIPT-010",
      "currency": "SGD",
      "total": 15.08,
      "method": "E-wallet",
      "timestamp": "2026-09-18T14:20:00+08:00",
      "lines": [
        {
          "label": "Base fare (surge \u00d71.20)",
          "amount": 3.6
        },
        {
          "label": "Distance fare (surge \u00d71.20)",
          "amount": 5.68
        },
        {
          "label": "Time fare (surge \u00d71.20)",
          "amount": 6.0
        },
        {
          "label": "Booking fee",
          "amount": 0.8
        },
        {
          "label": "Tolls",
          "amount": 1.0
        },
        {
          "label": "Promotion",
          "amount": -2.0
        }
      ]
    },
    "messages": [
      {
        "id": "MSG-010-1",
        "timestamp": "2026-09-18T13:57:00+08:00",
        "sender": "Driver",
        "text": "There may be traffic ahead. We could go via Lavender MRT."
      },
      {
        "id": "MSG-010-2",
        "timestamp": "2026-09-18T13:58:00+08:00",
        "sender": "Rider",
        "text": "Would that work? I need to get there soon."
      },
      {
        "id": "MSG-010-3",
        "timestamp": "2026-09-18T13:59:00+08:00",
        "sender": "Driver",
        "text": "I will try that road."
      }
    ],
    "events": [
      {
        "id": "APP-010-1",
        "timestamp": "2026-09-18T14:20:00+08:00",
        "title": "Trip completed",
        "detail": "Simulated trip completed. Vehicle GPS is supplied separately; no Rider device GPS was recorded."
      }
    ],
    "riderLocations": [],
    "locationNote": "No Rider device GPS was recorded. Shared simulated vehicle GPS is labelled separately.",
    "routeRecord": {
      "trip": {
        "trip_id": "TRIP-2026-ROUTE-010",
        "rider_id": "R-7823",
        "driver_id": "D-ROUTE-10",
        "pickup_location": {
          "name": "Bugis Junction",
          "lat": 1.299,
          "lng": 103.855
        },
        "dropoff_location": {
          "name": "Marina Bay Sands",
          "lat": 1.283,
          "lng": 103.86
        },
        "scheduled_time": "2026-09-18T14:00:00+08:00",
        "started_at": "2026-09-18T14:00:00+08:00",
        "completed_at": "2026-09-18T14:20:00+08:00",
        "currency": "SGD",
        "paid_net": "15.08"
      },
      "gps_telemetry": [
        {
          "timestamp": "2026-09-18T14:00:00+08:00",
          "lat": 1.299,
          "lng": 103.855
        },
        {
          "timestamp": "2026-09-18T14:01:00+08:00",
          "lat": 1.3006,
          "lng": 103.8566
        },
        {
          "timestamp": "2026-09-18T14:02:00+08:00",
          "lat": 1.3022,
          "lng": 103.8582
        },
        {
          "timestamp": "2026-09-18T14:03:00+08:00",
          "lat": 1.3038,
          "lng": 103.8598
        },
        {
          "timestamp": "2026-09-18T14:04:00+08:00",
          "lat": 1.3054,
          "lng": 103.8614
        },
        {
          "timestamp": "2026-09-18T14:05:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-18T14:06:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-18T14:07:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-18T14:08:00+08:00",
          "lat": 1.307,
          "lng": 103.863
        },
        {
          "timestamp": "2026-09-18T14:09:00+08:00",
          "lat": 1.305,
          "lng": 103.86275
        },
        {
          "timestamp": "2026-09-18T14:10:00+08:00",
          "lat": 1.303,
          "lng": 103.8625
        },
        {
          "timestamp": "2026-09-18T14:11:00+08:00",
          "lat": 1.301,
          "lng": 103.86225
        },
        {
          "timestamp": "2026-09-18T14:12:00+08:00",
          "lat": 1.299,
          "lng": 103.862
        },
        {
          "timestamp": "2026-09-18T14:13:00+08:00",
          "lat": 1.297,
          "lng": 103.86175
        },
        {
          "timestamp": "2026-09-18T14:14:00+08:00",
          "lat": 1.295,
          "lng": 103.8615
        },
        {
          "timestamp": "2026-09-18T14:15:00+08:00",
          "lat": 1.293,
          "lng": 103.86125
        },
        {
          "timestamp": "2026-09-18T14:16:00+08:00",
          "lat": 1.291,
          "lng": 103.861
        },
        {
          "timestamp": "2026-09-18T14:17:00+08:00",
          "lat": 1.289,
          "lng": 103.86075
        },
        {
          "timestamp": "2026-09-18T14:18:00+08:00",
          "lat": 1.287,
          "lng": 103.8605
        },
        {
          "timestamp": "2026-09-18T14:19:00+08:00",
          "lat": 1.285,
          "lng": 103.86025
        },
        {
          "timestamp": "2026-09-18T14:20:00+08:00",
          "lat": 1.283,
          "lng": 103.86
        }
      ],
      "route_baseline": {
        "source_id": "BASELINE-010",
        "simulated": true,
        "expected_minutes": "12.00",
        "points": [
          {
            "lat": 1.299,
            "lng": 103.855
          },
          {
            "lat": 1.291,
            "lng": 103.858
          },
          {
            "lat": 1.283,
            "lng": 103.86
          }
        ]
      },
      "route_landmarks": [
        {
          "id": "LANDMARK-LAVENDER-MRT",
          "name": "Lavender MRT",
          "lat": 1.307,
          "lng": 103.863
        }
      ],
      "tariff": {
        "base": "3.00",
        "km_rate": "1.20",
        "minute_rate": "0.25",
        "surge": "1.20",
        "booking": "0.80",
        "tolls": "1.00",
        "promo": "2.00"
      },
      "receipt": {
        "receipt_id": "RECEIPT-010",
        "trip_id": "TRIP-2026-ROUTE-010",
        "paid_net": "15.08",
        "currency": "SGD",
        "timestamp": "2026-09-18T14:20:00+08:00"
      }
    }
  }
]);
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
