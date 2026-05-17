-- ============================================================
-- 03_account_insights.sql
-- Purpose: PM / GTM strategy view — where to make the next bet
-- Audience: PM / Strategy / GTM Investments
-- ============================================================

-- ----------------------------------------
-- A: Cohort retention triangle
--    Rows: cohort month (Account creation)
--    Cols: months since cohort
--    Value: cumulative Won revenue
-- ----------------------------------------
WITH won AS (
    SELECT
        a.AccountId,
        DATE_TRUNC('month', a.CreatedDate)::DATE  AS cohort_month,
        DATE_TRUNC('month', o.CloseDate)::DATE    AS won_month,
        o.Amount
    FROM read_csv_auto('../data/Accounts.csv') a
    JOIN read_csv_auto('../data/Opportunities.csv') o USING (AccountId)
    WHERE o.Stage = '06 - Closed Won'
)
SELECT
    cohort_month,
    DATE_DIFF('month', cohort_month, won_month) AS months_since_cohort,
    SUM(Amount)                                 AS won_revenue
FROM won
WHERE DATE_DIFF('month', cohort_month, won_month) BETWEEN 0 AND 18
GROUP BY 1, 2
ORDER BY 1, 2;

-- ----------------------------------------
-- B: ARPA matrix by Segment × Industry
--    The wedge view — where high ARPA meets low account count
-- ----------------------------------------
SELECT
    a.Segment,
    a.Industry,
    COUNT(DISTINCT a.AccountId)                                           AS account_count,
    COUNT(DISTINCT CASE WHEN o.Stage = '06 - Closed Won' THEN a.AccountId END) AS won_account_count,
    SUM(CASE WHEN o.Stage = '06 - Closed Won' THEN o.Amount ELSE 0 END)   AS won_revenue,
    SUM(CASE WHEN o.Stage = '06 - Closed Won' THEN o.Amount ELSE 0 END)
        / NULLIF(COUNT(DISTINCT CASE WHEN o.Stage = '06 - Closed Won' THEN a.AccountId END), 0) AS arpa
FROM read_csv_auto('../data/Accounts.csv') a
LEFT JOIN read_csv_auto('../data/Opportunities.csv') o USING (AccountId)
GROUP BY 1, 2
HAVING COUNT(DISTINCT CASE WHEN o.Stage = '06 - Closed Won' THEN a.AccountId END) > 0
ORDER BY arpa DESC;

-- ----------------------------------------
-- C: Loss reason Pareto
-- ----------------------------------------
SELECT
    LossReason,
    COUNT(*)                                          AS lost_deal_count,
    SUM(Amount)                                       AS lost_revenue,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct_of_losses
FROM read_csv_auto('../data/Opportunities.csv')
WHERE Stage = '07 - Closed Lost'
GROUP BY 1
ORDER BY lost_deal_count DESC;

-- ----------------------------------------
-- D: Win rate by Industry
-- ----------------------------------------
SELECT
    a.Industry,
    COUNT(DISTINCT CASE WHEN o.Stage IN ('06 - Closed Won', '07 - Closed Lost') THEN o.OppId END) AS closed_count,
    COUNT(DISTINCT CASE WHEN o.Stage = '06 - Closed Won' THEN o.OppId END)                        AS won_count,
    ROUND(
        COUNT(DISTINCT CASE WHEN o.Stage = '06 - Closed Won' THEN o.OppId END) * 100.0
        / NULLIF(COUNT(DISTINCT CASE WHEN o.Stage IN ('06 - Closed Won', '07 - Closed Lost') THEN o.OppId END), 0),
        1
    ) AS win_rate_pct
FROM read_csv_auto('../data/Accounts.csv') a
JOIN read_csv_auto('../data/Opportunities.csv') o USING (AccountId)
GROUP BY 1
HAVING closed_count >= 5
ORDER BY win_rate_pct DESC;

-- ----------------------------------------
-- E: Top accounts by Won revenue
-- ----------------------------------------
SELECT
    a.AccountId,
    a.AccountName,
    a.Industry,
    a.Segment,
    a.Region,
    SUM(o.Amount) FILTER (WHERE o.Stage = '06 - Closed Won') AS won_revenue,
    COUNT(*)      FILTER (WHERE o.Stage = '06 - Closed Won') AS won_deal_count
FROM read_csv_auto('../data/Accounts.csv')     a
JOIN read_csv_auto('../data/Opportunities.csv') o USING (AccountId)
GROUP BY 1, 2, 3, 4, 5
HAVING SUM(o.Amount) FILTER (WHERE o.Stage = '06 - Closed Won') > 0
ORDER BY won_revenue DESC
LIMIT 20;
