# 06: Route Deviation resolved end to end

**What to build:** The second required Dispute Category. A rider files "the driver took a longer route and I was overcharged" and the system resolves it. Code compares the actual route with the optimal route, finds unexpected stops, compares expected and actual duration, and reads the fare breakdown including surge and promo. Route Deviation uses the shared Waypoint clauses (R-04, D-04, with R-03 and D-03 for the fare). They state no refund formula, so how a partial refund is calculated is a code rule recorded in an ADR before building, as ADR 0002 does for the No-Show thresholds (contract-decisions item 9). There are three mock cases: one the rider should win, one the driver should win (for example a rider-requested detour shown in chat), and one ambiguous.

**Blocked by:** 04, 05

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Kyven (policy clauses with Braedon)

- [ ] Actual and optimal route distance, unexpected stops and duration difference are computed by code and stored as Evidence Items
- [ ] The fare breakdown is available as evidence, including surge and promo
- [ ] Route Deviation clauses are served for the category, and the refund calculation is a recorded code rule shown in the Ruling's calculation
- [ ] Three Route Deviation mock cases exist with separate expected-outcome labels
- [ ] A rider-requested detour in chat is found and cited by the Driver Advocate
- [ ] The Ruling amount for a partial refund matches the calculation recomputed by code
- [ ] All three mock cases resolve end to end with the expected outcome
- [ ] The No-Show mock cases still pass
