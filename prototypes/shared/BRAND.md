# Waypoint

**A clearer way forward.**

Waypoint is an independent ride-hailing experience prototype. Ride planning is the main task; trip history and receipts follow the booking area, and filing a report is optional support. Ryde remains the source of the sample dispute and rider trip records; no live integration is implied. The 3D trip scene uses invented locations and conversation, separate from the rider evidence collector.

## Visual identity

The design uses charcoal framing, white work surfaces, fine map lines, restrained dot textures and blue actions. Meuze's website informed the editorial direction; the logo, route artwork and mascot are original SVG drawings.

| Role | Colour |
| --- | --- |
| Page and navigation | `#0D1218` |
| Work surfaces | `#FFFFFF` |
| Primary actions | `#315CF5` |
| Links on light surfaces | `#2851DC` |
| Main text on light surfaces | `#17202D` |
| Secondary text on dark surfaces | `#AEB9C9` |

Use locally hosted Nunito for headings, interface text and reference labels, with Segoe UI / system sans-serif as fallbacks. Its rounded forms and restrained letter spacing keep the interface approachable. Raw evidence JSON retains monospace formatting for readability. Keep important actions clearly labelled. Status is expressed in words as well as colour. The font's SIL Open Font License is included in `fonts/OFL-Nunito.txt`.

## Assets

- `waypoint-mark.svg`: route-shaped W logo, also used as the favicon. Pair with the Waypoint wordmark.
- `pip.svg`: Pip, a small compass-guide mascot. Used for friendly guidance, not as a claim of live chat or human support.
- `waypoint-route.svg`: decorative schematic city route. It is not GPS evidence or an actual trip map.
- `waypoint-car.svg`: decorative trip icon.
- `journey.js` / `journey.css`: switchable, playable CSS 3D journey scene; rider and driver views, route scrubbing and stage jumps.
- `experience.js` / `experience.css`: scroll reveals and ride-hailing entry flow.
- `waypoint.css`: the active shared styling for trip overview, receipts, messages, evidence collection, form details, uploads, review and completion.

All assets work locally without an external image service. Decorative images use empty alternative text; standalone Pip portraits have descriptive alternative text. Reduced-motion preferences are respected.
