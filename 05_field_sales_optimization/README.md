# Phase 5 — Field Sales Optimization 🚧

**Status:** Planned, not yet built. This is the phase most directly relevant to high-impact field operations work.

This is the visualization phase tying the analytical framework to a real operational problem: allocating a finite field-heavy GTM team across a high-cardinality account base.

## The actual problem

A finite field-heavy GTM team. A high-cardinality account base. Finite hours per week. How do you decide which reps cover which accounts in what order?

In practice, this allocation is driven by a stack of operational tooling (data warehouse + BI + dispatch tooling), bridging to a unified SFA. Phase 5 will visualize the *analytical layer* under that allocation, on synthetic data.

## Planned outputs

### Geographic visualization
- **Account density × value-potential heatmap** — Plotly with map tiles, colored by potential value, sized by acquisition probability
- **Territory boundary visualization** — Voronoi partitioning over rep locations vs. administrative ward boundaries; which model best matches actual reachable time-by-transit

### Visit-vs-Call decision logic
- **Hybrid scoring model** — given an account's potential value, geographic accessibility, decision-maker availability, and historical responsiveness, what's the expected ROI per hour of (a) in-person visit, (b) phone call, (c) email outreach?
- **Day-plan optimization** — given a rep's assigned accounts, a starting location, and 8 working hours, produce an ordered visit plan that maximizes expected acquisition value

### Effectiveness measurement
- **Lift analysis** — Did the visit move the deal? Comparing matched pairs of visited-vs-called accounts with similar baseline characteristics
- **Capacity vs coverage** — at current rep count, what % of high-value accounts can we touch monthly? What's the marginal value of one additional rep?

## Why this matters

This is the highest-impact problem in field-heavy, high-frequency B2B operations.

For any role that involves field operations, capacity planning, or geographic optimization, this phase is the one most worth reading.

---

*This is the phase most worth waiting for. Target: summer/fall 2026.*
