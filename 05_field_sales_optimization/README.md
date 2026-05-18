# Phase 5 — Field Sales Optimization 🚧

**Status:** Planned, not yet built. This is the phase most directly relevant to high-impact field operations work.

This is the visualization phase tying the analytical framework to a real operational problem: large field sales team allocation across a high-cardinality merchant base.

## The actual problem

A field sales team of around one hundred reps. Tens of thousands of merchants. Finite hours per week. How do you decide which reps visit which merchants in what order?

In practice, this allocation is driven by a stack of operational tooling (data warehouse + BI + dispatch tooling), bridging to a unified SFA. Phase 5 will visualize the *analytical layer* under that allocation, on synthetic data.

## Planned outputs

### Geographic visualization
- **Merchant density × GMV potential heatmap** — Plotly with map tiles, colored by potential value, sized by acquisition probability
- **Territory boundary visualization** — Voronoi partitioning over rep locations vs. administrative ward boundaries; which model best matches actual reachable time-by-transit

### Visit-vs-Call decision logic
- **Hybrid scoring model** — given a merchant's potential GMV, geographic accessibility, decision-maker availability, and historical responsiveness, what's the expected ROI per hour of (a) in-person visit, (b) phone call, (c) email outreach?
- **Day-plan optimization** — given a rep's assigned merchants, a starting location, and 8 working hours, produce an ordered visit plan that maximizes expected acquisition value

### Effectiveness measurement
- **Lift analysis** — Did the visit move the deal? Comparing matched pairs of visited-vs-called merchants with similar baseline characteristics
- **Capacity vs coverage** — at current rep count, what % of high-value merchants can we touch monthly? What's the marginal value of one additional rep?

## Why this matters

This is the highest-impact problem in last-mile logistics, on-demand services, and any field-heavy B2B sales business.

For any role that involves field operations, capacity planning, or geographic optimization (delivery/marketplace operations, B2B field sales strategy, GTM Investments analysis, etc.), this phase is the one most worth reading.

---

*This is the phase most worth waiting for. Target: summer/fall 2026.*
