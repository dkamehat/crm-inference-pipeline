-- ============================================================
-- 02_pipeline_health.sql
-- Purpose: Sales manager view — where is pipeline stuck?
-- Audience: Sales Manager / Front-line ops
-- ============================================================

-- ----------------------------------------
-- A: Stage funnel (count of opps at or past each stage)
-- ----------------------------------------
WITH stages AS (
    SELECT * FROM (VALUES
        ('01 - Prospecting',  1),
        ('02 - Qualification',2),
        ('03 - Needs Analysis',3),
        ('04 - Proposal',     4),
        ('05 - Negotiation',  5),
        ('06 - Closed Won',   6)
    ) AS t(stage_name, stage_order)
)
SELECT
    s.stage_name,
    s.stage_order,
    COUNT(DISTINCT o.OppId) AS opps_at_or_past_stage
FROM stages s
LEFT JOIN read_csv_auto('../data/Opportunities.csv') o
    ON (CAST(SUBSTRING(o.Stage, 1, 2) AS INT) >= s.stage_order
        AND o.Stage <> '07 - Closed Lost')
GROUP BY 1, 2
ORDER BY 2;

-- ----------------------------------------
-- B: Stage-to-stage conversion rates
-- ----------------------------------------
WITH stage_counts AS (
    SELECT
        CAST(SUBSTRING(Stage, 1, 2) AS INT) AS stage_order,
        COUNT(DISTINCT OppId)               AS opps
    FROM read_csv_auto('../data/Opportunities.csv')
    WHERE Stage NOT LIKE '07%'
    GROUP BY 1
),
ordered AS (
    SELECT
        stage_order,
        opps,
        LEAD(opps) OVER (ORDER BY stage_order) AS next_opps
    FROM stage_counts
)
SELECT
    stage_order || ' -> ' || (stage_order + 1) AS transition,
    opps,
    next_opps,
    ROUND(next_opps * 100.0 / NULLIF(opps, 0), 1) AS conversion_pct
FROM ordered
WHERE next_opps IS NOT NULL
ORDER BY stage_order;

-- ----------------------------------------
-- C: Stage duration distribution (days from create to current/close)
-- ----------------------------------------
SELECT
    Stage,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY days_open) AS p25_days,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY days_open) AS median_days,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY days_open) AS p75_days,
    MAX(days_open)                                          AS max_days,
    COUNT(*)                                                AS opp_count
FROM (
    SELECT
        Stage,
        CASE
            WHEN Stage IN ('06 - Closed Won', '07 - Closed Lost')
                THEN DATE_DIFF('day', CreatedDate, CloseDate)
            ELSE DATE_DIFF('day', CreatedDate, CURRENT_DATE)
        END AS days_open
    FROM read_csv_auto('../data/Opportunities.csv')
)
GROUP BY Stage
ORDER BY Stage;

-- ----------------------------------------
-- D: Stuck deals (open, >60 days, sorted by size)
-- ----------------------------------------
SELECT
    o.OppId,
    a.AccountName  AS account_name,
    o.Stage,
    o.Amount,
    DATE_DIFF('day', o.CreatedDate, CURRENT_DATE) AS days_open,
    u.OwnerName AS rep_name
FROM read_csv_auto('../data/Opportunities.csv') o
JOIN read_csv_auto('../data/Accounts.csv')      a USING (AccountId)
JOIN read_csv_auto('../data/Users.csv')         u USING (OwnerId)
WHERE o.Stage NOT IN ('06 - Closed Won', '07 - Closed Lost')
  AND DATE_DIFF('day', o.CreatedDate, CURRENT_DATE) > 60
ORDER BY o.Amount DESC
LIMIT 20;

-- ----------------------------------------
-- E: Rep scorecard
-- ----------------------------------------
SELECT
    u.OwnerName                                                      AS rep,
    u.Region,
    COUNT(*)        FILTER (WHERE o.Stage NOT LIKE '06%' AND o.Stage NOT LIKE '07%') AS open_opp_count,
    SUM(o.Amount)   FILTER (WHERE o.Stage NOT LIKE '06%' AND o.Stage NOT LIKE '07%') AS open_pipeline,
    SUM(o.Amount * o.Probability) FILTER (WHERE o.Stage NOT LIKE '06%' AND o.Stage NOT LIKE '07%') AS weighted_pipeline,
    SUM(o.Amount)   FILTER (WHERE o.Stage = '06 - Closed Won')       AS won_revenue,
    COUNT(*)        FILTER (WHERE o.Stage = '06 - Closed Won') * 1.0
        / NULLIF(COUNT(*) FILTER (WHERE o.Stage IN ('06 - Closed Won', '07 - Closed Lost')), 0) AS win_rate,
    AVG(CASE WHEN o.Stage = '06 - Closed Won'
             THEN DATE_DIFF('day', o.CreatedDate, o.CloseDate) END) AS avg_cycle_days_won
FROM read_csv_auto('../data/Opportunities.csv') o
JOIN read_csv_auto('../data/Users.csv')         u USING (OwnerId)
GROUP BY 1, 2
ORDER BY won_revenue DESC NULLS LAST;
