# Phase 1 — B2B SaaS

> Sales operations and Customer Success analytics for a fictional B2B SaaS business.
> 800 accounts, ~1,300 opportunities, 331 active customers. Synthetic data only.
>
> This is the **conventional-craft companion** to the flagship inference pipeline in
> [`../00_foundation/`](../00_foundation/): the SQL + BI work a BizOps analyst ships
> day-to-day. The flagship shows it can be made *provable*; this shows the everyday
> fluency it builds on. Each analysis closes with a **Design Note** — the decision it
> supports and the trade-offs deliberately left out.

---

## What's in this folder

```
01_b2b_saas/
├── README.md                    ← you are here
├── data/                        7 CSVs, Salesforce-shaped schema
│   ├── Accounts.csv             800 rows
│   ├── Opportunities.csv        ~1,300 rows
│   ├── Activities.csv           ~12,000 rows
│   ├── Users.csv                12 reps
│   ├── Subscriptions.csv        331 customers (those with Closed Won)
│   ├── UsageMetrics.csv         ~3,600 monthly usage rows
│   └── HealthScores.csv         331 current health snapshots
├── sql/
│   ├── 01_sales_performance.sql        Won revenue, win rate, cycle, ARPA
│   ├── 02_pipeline_health.sql          Funnel, stuck deals, rep scorecard
│   ├── 03_account_insights.sql         Cohort retention, ARPA matrix, loss-reason Pareto
│   └── 04_customer_health.sql          ARR retention, MAU trends, renewal risk
└── notebooks/
    └── analysis.ipynb           Plotly-rendered analysis — outputs are committed,
                                 so it renders inline on GitHub (no run needed)
```

---

## How to read this

The intent is for the **notebook to be the primary deliverable**. Each section in the notebook:

1. States the question being asked
2. Runs the SQL (queries are also independently available in `sql/`)
3. Produces an interactive Plotly chart
4. Closes with **Design Notes** — what decision this view supports, what trade-offs are deliberately not shown

The notebook is structured so a reviewer can answer "is this analysis well-reasoned?" in under five minutes by reading only the Design Notes blocks.

---

## Schema

### Sales objects (Salesforce standard)

| Object | Key fields |
|---|---|
| Accounts | AccountId, Industry, Region, Segment, AccountOwner, CreatedDate |
| Opportunities | OppId, AccountId, Stage, Amount, Probability, CreatedDate, CloseDate, OwnerId, LossReason |
| Activities | ActivityId, OppId, ActivityType, ActivityDate, OwnerId, DurationMin |
| Users | OwnerId, OwnerName, Role, Region |

Stage values are prefixed `01 - Prospecting` through `06 - Closed Won` / `07 - Closed Lost` so string-sorted is also stage-sorted.

### Customer Success objects

| Object | Key fields |
|---|---|
| Subscriptions | SubscriptionId, AccountId, Plan, ARR, StartDate, RenewalDate, Status, Seats |
| UsageMetrics | UsageId, AccountId, SubscriptionId, Month, Seats, MAU, MAURatio, Sessions, FeatureAdoptionRate |
| HealthScores | AccountId, SubscriptionId, HealthScore (0-100), HealthBand (Green/Yellow/Red), NPS, LastQBR, CSMOwner |

### Joins

```
Accounts (AccountId) ──┬── Opportunities ──── Users (OwnerId)
                       │
                       └── Subscriptions ──── HealthScores (SubscriptionId)
                                          └── UsageMetrics (SubscriptionId)
```

---

## Four analyses

### 1. Sales Performance Overview
*"Are we on track this quarter, and where is the variance coming from?"*

Won revenue, win rate, average deal size, sales cycle, region heatmap, industry × segment treemap.

### 2. Pipeline Health
*"Where is pipeline stuck, and who needs help?"*

Stage funnel, stage-to-stage conversion, stage duration distribution, stuck-deal watchlist, rep scorecard.

### 3. Account Insights
*"Which segments compound, and where is the leak?"*

Cohort retention triangle, ARPA matrix by segment × industry, loss-reason Pareto, win rate by industry, top accounts.

### 4. Customer Health
*"Which customers will churn or expand next?"*

Active ARR, gross retention, NPS distribution, MAU ratio trend by cohort, feature adoption matrix, renewal risk watchlist.

---

## Distribution check

For transparency, here are the actual distributions baked into the synthetic data:

| Dimension | Distribution |
|---|---|
| Subscription status | Active 77% / At Risk 13% / Churned 10% |
| Health band | Green 44% / Yellow 46% / Red 10% |
| Plan mix | Starter 25% / Growth 41% / Business 23% / Enterprise 10% |
| Stages | Closed Won 30% / Closed Lost 25% / Active pipeline 45% |

These were chosen to be plausible for a real B2B SaaS in growth stage — not perfectly clean, not pathological.

---

## 日本語サマリ

架空の B2B SaaS 事業に対する **SalesOps / カスタマーサクセス分析**です（口座800・
商談約1,300・有効顧客331、すべて合成データ）。中核の推論パイプライン
[`../00_foundation/`](../00_foundation/) が「分析を*証明可能*にできる」ことを示すのに対し、
こちらは BizOps アナリストが日々こなす **王道の SQL / BI の地力**を示します。

主役は**ノートブック**。各セクションは ①問いの明示 → ②SQL 実行（クエリは `sql/` にも
単独で配置）→ ③Plotly インタラクティブ図 → ④**Design Note**（その図がどの意思決定を
支えるか、何をあえて見せないか）で構成。レビュアーが Design Note だけ読めば「この分析は
筋が良いか」を5分で判断できるように設計しています。出力はコミット済みのため GitHub 上で
そのまま描画されます。4分析：①セールス実績 ②パイプライン健全性 ③口座インサイト
④顧客ヘルス。実ドメインの指紋はゼロ（標準的な CRM オブジェクトモデルに準拠）。
