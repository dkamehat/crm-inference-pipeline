# Phase 4 — Advanced Analytics with pandas 🚧

**Status:** Planned, not yet built.

Where Phases 1–3 establish the analytical framework, **Phase 4 goes deeper with pandas**. Same data, more sophisticated analyses.

## Planned scope

### `pandas_deep_dive/`
- **Cohort retention triangles** — full pandas implementation (not just chart output)
- **Customer lifetime value** — using subscription + churn data from Phase 1
- **Revenue waterfall** — new vs expansion vs contraction vs churn, month over month
- **Pipeline velocity** — distribution of time-in-stage by stage, with anomaly flags

### `ml_lite/`
- **Lead scoring** — logistic regression on Opportunities × Activities features to predict win probability
- **Churn prediction** — gradient boosting on usage metrics + NPS + tenure
- **Renewal risk classifier** — binary classification of "renew vs churn" at the 90-day mark

The intent is to demonstrate pandas-as-analysis-engine, not just pandas-as-data-shaping. The ML pieces are intentionally "lite" — feature engineering and interpretability over model complexity.

## Why this exists

A practitioner who can prototype a lead-scoring model in pandas before handing it off to a data scientist is fundamentally different from one who can only write a brief. This phase makes that capability legible.

---

*Will be built after Phases 1-3 are stable.*
