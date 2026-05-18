# Sales Analytics Portfolio

> Sales operations and customer success analytics, built on Salesforce-shaped data.
> Same framework applied across three businesses. SQL, Python (pandas), Plotly.

**Status:** Active — building incrementally
**Last update:** 2026-05-17

---

## What this is

This repository visualizes the design thinking behind sales operations and customer success programs, rendered as **SQL + Python + interactive charts** on synthetic data. The three business domains share one analytical framework.

The framework in this repository reflects design thinking applied to large-scale sales operations in B2B environments. All data and identifiers in this repository are synthetic.

The framework, not the domain, is the asset.

---

## Repository structure

```
sales-analytics-portfolio/
├── 01_b2b_saas/             ✅ Phase 1 — published
│   ├── data/                Synthetic Salesforce-shaped CSVs (Sales + CS)
│   ├── sql/                 4 query sets (Performance, Pipeline, Accounts, CS)
│   ├── notebooks/           Interactive Plotly analysis (Jupyter)
│   └── images/              Static chart renders for previews
├── 03_ec_marketplace/       🚧 Phase 3 — planned
├── 04_advanced_analytics/   🚧 Phase 4 — planned
│   ├── pandas_deep_dive/    Cohort/retention/LTV with pandas
│   └── ml_lite/             Lead scoring, churn prediction (sklearn)
└── 05_field_sales_optimization/   🚧 Phase 5 — planned
    └── (Real-world feature: visit-routing logic for field sales reps)
```

The phases beyond Phase 1 are scoped and stubbed — each will be added incrementally as time allows.

---

## Phase 1 — B2B SaaS (✅ Published)

Synthetic B2B SaaS business with 800 accounts, ~1,300 opportunities, 331 active customers. Schema mirrors Salesforce standard objects, extended with CS tables.

**Four analyses:**

| # | Analysis | Audience | Read first |
|---|---|---|---|
| 1 | Sales Performance Overview | Exec / CRO | If you care about top-line revenue trajectory |
| 2 | Pipeline Health | Sales Manager | If you care about where deals get stuck |
| 3 | Account Insights | PM / GTM Strategy | If you care about which segments compound |
| 4 | Customer Health | CS Manager | If you care about retention and renewal risk |

**Open the notebook:** [`01_b2b_saas/notebooks/analysis.ipynb`](./01_b2b_saas/notebooks/analysis.ipynb) — GitHub renders the embedded Plotly charts inline.

---

## Phase 3 — EC Marketplace (🚧 Planned)

Seller acquisition for a fictional EC marketplace. Tests whether the framework holds for a transactional high-volume business with very different unit economics.

---

## Phase 4 — Advanced Analytics with pandas (🚧 Planned)

Where Phase 1–3 establish the framework on synthetic data, Phase 4 goes deeper with the same data:

- **Cohort retention triangles** — pandas-native implementation
- **Customer lifetime value** — using subscription + churn data from Phase 1
- **Lead scoring** — logistic regression on Opportunities × Activities to predict win probability
- **Anomaly detection** — pipeline velocity outliers, week-over-week deal stuckness

This phase demonstrates pandas-as-analysis-engine, not just pandas-as-data-shaping.

---

## Phase 5 — Field Sales Optimization (🚧 Planned)

The challenge: a finite field sales team, tens of thousands of merchants, finite hours per week. How do you decide which reps visit which merchants in what order?

Planned outputs:

- **Geographic heatmap** of merchant density × GMV potential (Plotly with map tiles)
- **Territory boundary visualization** — Voronoi partitioning vs administrative wards
- **Visit-call hybrid scoring** — when is in-person visit worth the time, when is a phone call enough
- **Routing efficiency** — given a rep's assigned merchants, what's the optimal day plan

This is the highest-impact piece for any PM/Ops role in last-mile logistics, on-demand services, or field-heavy B2B sales.

---

## Technical stack

| Layer | Tool | Why |
|---|---|---|
| Data | CSV (synthetic, seeded) | Reproducible without infrastructure |
| Query | SQL (DuckDB-compatible) | Queries run on flat files, no warehouse needed |
| Analysis | Python 3.11 + pandas | Industry default |
| Visualization | Plotly | Interactive, renders inline in Jupyter and GitHub |
| Notebooks | Jupyter | Standard, GitHub-rendered |

To run notebooks locally:

```bash
git clone https://github.com/dkamehat/sales-analytics-portfolio.git
cd sales-analytics-portfolio
pip install -r requirements.txt
jupyter lab
```

---

## A note on synthetic data

All CSVs in this repository are **synthetically generated** with seeded random number generators (reproducible). No real customer, account, or transaction data appears anywhere. The seed and generation scripts are included.

The schema mirrors Salesforce standard objects (Accounts, Opportunities, Activities, Users) extended with CS objects (Subscriptions, UsageMetrics, HealthScores) — chosen so that the patterns explored generalize directly to real Salesforce-driven GTM stacks.

---

## License

MIT for code. The synthetic data is offered as-is for portfolio review purposes.
