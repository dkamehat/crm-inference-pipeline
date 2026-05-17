-- ============================================================
-- 01_sales_performance.sql
-- Purpose: Executive view — are we on track this quarter?
-- Audience: CRO / Sales Leader
-- DB: DuckDB-compatible (works on flat CSVs via read_csv_auto)
-- ============================================================

-- ----------------------------------------
-- KPI 1: Won revenue, win rate, avg deal size, cycle (overall)
-- ----------------------------------------
WITH closed AS (
    SELECT
        OppId,
        AccountId,
        Stage,
        Amount,
        CreatedDate,
        CloseDate,
        CASE WHEN Stage = '06 - Closed Won'  THEN 1 ELSE 0 END AS is_won,
        CASE WHEN Stage = '07 - Closed Lost' THEN 1 ELSE 0 END AS is_lost
    FROM read_csv_auto('../data/Opportunities.csv')
    WHERE Stage IN ('06 - Closed Won', '07 - Closed Lost')
)
SELECT
    SUM(CASE WHEN is_won = 1 THEN Amount ELSE 0 END)             AS won_revenue,
    SUM(is_won) * 1.0 / NULLIF(SUM(is_won + is_lost), 0)          AS win_rate,
    AVG(CASE WHEN is_won = 1 THEN Amount END)                    AS avg_deal_size_won,
    AVG(CASE WHEN is_won = 1 THEN DATE_DIFF('day', CreatedDate, CloseDate) END) AS avg_sales_cycle_days,
    COUNT(*)                                                     AS closed_deal_count
FROM closed;

-- ----------------------------------------
-- KPI 2: Revenue trend by month
-- ----------------------------------------
SELECT
    DATE_TRUNC('month', CloseDate)::DATE AS month,
    SUM(Amount) FILTER (WHERE Stage = '06 - Closed Won') AS won_revenue,
    COUNT(*)    FILTER (WHERE Stage = '06 - Closed Won') AS won_count
FROM read_csv_auto('../data/Opportunities.csv')
WHERE CloseDate >= '2025-01-01'
GROUP BY 1
ORDER BY 1;

-- ----------------------------------------
-- KPI 3: Region × Quarter heatmap
-- ----------------------------------------
SELECT
    a.Region                                          AS region,
    DATE_TRUNC('quarter', o.CloseDate)::DATE          AS quarter,
    SUM(o.Amount) FILTER (WHERE o.Stage = '06 - Closed Won') AS won_revenue
FROM read_csv_auto('../data/Opportunities.csv') o
JOIN read_csv_auto('../data/Accounts.csv')      a USING (AccountId)
WHERE o.CloseDate >= '2025-01-01'
GROUP BY 1, 2
ORDER BY 1, 2;

-- ----------------------------------------
-- KPI 4: Industry × Segment treemap base
-- ----------------------------------------
SELECT
    a.Industry,
    a.Segment,
    SUM(o.Amount) FILTER (WHERE o.Stage = '06 - Closed Won') AS won_revenue,
    COUNT(DISTINCT o.AccountId) FILTER (WHERE o.Stage = '06 - Closed Won') AS won_account_count
FROM read_csv_auto('../data/Opportunities.csv') o
JOIN read_csv_auto('../data/Accounts.csv')      a USING (AccountId)
GROUP BY 1, 2
HAVING SUM(o.Amount) FILTER (WHERE o.Stage = '06 - Closed Won') > 0
ORDER BY won_revenue DESC;

-- ----------------------------------------
-- KPI 5: Rep quota attainment (assume $5M per rep per year)
-- ----------------------------------------
WITH rep_won AS (
    SELECT
        u.OwnerName,
        u.Role,
        u.Region,
        SUM(o.Amount) FILTER (WHERE o.Stage = '06 - Closed Won') AS won_amount
    FROM read_csv_auto('../data/Opportunities.csv') o
    JOIN read_csv_auto('../data/Users.csv')         u USING (OwnerId)
    WHERE o.CloseDate >= '2025-06-01'  -- trailing year
    GROUP BY 1, 2, 3
)
SELECT
    OwnerName,
    Role,
    Region,
    won_amount,
    5000000           AS annual_quota,
    won_amount / 5000000.0  AS attainment_rate
FROM rep_won
ORDER BY attainment_rate DESC;
