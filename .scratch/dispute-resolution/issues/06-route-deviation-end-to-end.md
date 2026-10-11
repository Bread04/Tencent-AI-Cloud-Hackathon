# 06: Route Deviation resolved end to end

**What to build:** The second required Dispute Category. A rider files "the driver took a longer route and I was overcharged" and the system resolves it. Code compares the actual route with the optimal route, finds unexpected stops, compares expected and actual duration, and reads the fare breakdown including surge and promo. Mock policy gains the route deviation clauses, including how a partial refund is calculated. There are three mock cases: one the rider should win, one the driver should win (for example a rider-requested detour shown in chat), and one ambiguous.

**Blocked by:** 04, 05

**Status:** ready-for-agent

**Tier:** 0 · **Owner:** Kyven (policy clauses with Braedon)

- [ ] Actual and optimal route distance, unexpected stops and duration difference are computed by code and stored as Evidence Items
- [ ] The fare breakdown is available as evidence, including surge and promo
- [ ] Route deviation Policy Clauses exist with stable IDs, including the refund calculation
- [ ] Three Route Deviation mock cases exist with separate expected-outcome labels
- [ ] A rider-requested detour in chat is found and cited by the Driver Advocate
- [ ] The Ruling amount for a partial refund matches the calculation recomputed by code
- [ ] All three mock cases resolve end to end with the expected outcome
- [ ] The No-Show mock cases still pass
