-- ============================================================
-- 04_customer_health.sql
-- Purpose: CS Manager view — who will churn or expand?
-- Audience: CS Manager / CSM Lead (Notion Manager CS, Enterprise CSM)
-- ============================================================

-- ----------------------------------------
-- KPI block: Active ARR, Gross Retention, Avg NPS, Red account count
-- ----------------------------------------
WITH base AS (
    SELECT
        s.SubscriptionId,
        s.AccountId,
        s.Plan,
        s.ARR,
        s.Status,
        s.RenewalDate,
        h.HealthScore,
        h.HealthBand,
        h.NPS
    FROM read_csv_auto('../data/Subscriptions.csv') s
    LEFT JOIN read_csv_auto('../data/HealthScores.csv') h
        ON s.SubscriptionId = h.SubscriptionId
)
SELECT
    SUM(CASE WHEN Status = 'Active'  THEN ARR ELSE 0 END)              AS active_arr,
    SUM(CASE WHEN Status = 'Churned' THEN ARR ELSE 0 END)              AS churned_arr,
    SUM(ARR)                                                           AS total_arr,
    1.0 - SUM(CASE WHEN Status = 'Churned' THEN ARR ELSE 0 END)
        / NULLIF(SUM(ARR), 0)                                          AS gross_retention,
    AVG(NPS)                                                           AS avg_nps,
    COUNT(*) FILTER (WHERE HealthBand = 'Red')                         AS red_account_count
FROM base;

-- ----------------------------------------
-- Health band distribution
-- ----------------------------------------
SELECT
    HealthBand,
    COUNT(*)                              AS account_count,
    SUM(s.ARR)                            AS total_arr,
    AVG(h.HealthScore)                    AS avg_health_score
FROM read_csv_auto('../data/Subscriptions.csv') s
JOIN read_csv_auto('../data/HealthScores.csv')  h USING (SubscriptionId)
GROUP BY HealthBand
ORDER BY CASE HealthBand WHEN 'Green' THEN 1 WHEN 'Yellow' THEN 2 WHEN 'Red' THEN 3 END;

-- ----------------------------------------
-- NPS distribution by band
-- ----------------------------------------
SELECT
    HealthBand,
    FLOOR(NPS / 10) * 10  AS nps_bucket_floor,
    COUNT(*)              AS count_in_bucket
FROM read_csv_auto('../data/HealthScores.csv')
GROUP BY 1, 2
ORDER BY 1, 2;

-- ----------------------------------------
-- MAU ratio trend by Plan (last 12 months)
-- ----------------------------------------
SELECT
    s.Plan,
    DATE_TRUNC('month', u.Month)::DATE AS month,
    AVG(u.MAURatio)                    AS avg_mau_ratio,
    COUNT(DISTINCT u.SubscriptionId)   AS active_subscriptions
FROM read_csv_auto('../data/UsageMetrics.csv') u
JOIN read_csv_auto('../data/Subscriptions.csv') s USING (SubscriptionId)
WHERE u.Month >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL 12 MONTH)::DATE
GROUP BY 1, 2
ORDER BY 1, 2;

-- ----------------------------------------
-- Feature adoption matrix: Plan × adoption band
-- ----------------------------------------
WITH latest_adoption AS (
    SELECT
        u.SubscriptionId,
        AVG(u.FeatureAdoptionRate) AS avg_adoption  -- last-quarter average
    FROM read_csv_auto('../data/UsageMetrics.csv') u
    WHERE u.Month >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL 3 MONTH)::DATE
    GROUP BY 1
)
SELECT
    s.Plan,
    CASE
        WHEN la.avg_adoption <  0.4 THEN 'Low'
        WHEN la.avg_adoption <  0.7 THEN 'Mid'
        ELSE                              'High'
    END                                AS adoption_band,
    COUNT(DISTINCT s.SubscriptionId)   AS subscription_count,
    SUM(s.ARR)                         AS arr_in_band
FROM read_csv_auto('../data/Subscriptions.csv') s
JOIN latest_adoption la USING (SubscriptionId)
GROUP BY 1, 2
ORDER BY s.Plan,
    CASE adoption_band WHEN 'Low' THEN 1 WHEN 'Mid' THEN 2 WHEN 'High' THEN 3 END;

-- ----------------------------------------
-- Renewal Risk Watchlist
-- (Red or Yellow band, renewing in next 90 days, sorted by ARR)
-- ----------------------------------------
SELECT
    s.AccountId,
    a.AccountName,
    s.Plan,
    s.ARR,
    h.HealthBand,
    h.HealthScore,
    h.NPS,
    s.RenewalDate,
    DATE_DIFF('day', CURRENT_DATE, s.RenewalDate) AS days_to_renewal,
    h.CSMOwner
FROM read_csv_auto('../data/Subscriptions.csv') s
JOIN read_csv_auto('../data/Accounts.csv')      a USING (AccountId)
JOIN read_csv_auto('../data/HealthScores.csv')  h USING (SubscriptionId)
WHERE s.Status <> 'Churned'
  AND DATE_DIFF('day', CURRENT_DATE, s.RenewalDate) BETWEEN 0 AND 90
  AND h.HealthBand IN ('Red', 'Yellow')
ORDER BY s.ARR DESC
LIMIT 25;
