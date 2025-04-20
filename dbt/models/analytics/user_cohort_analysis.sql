-- models/analytics/user_cohort_analysis.sql
{{ config(schema='analytics') }}

WITH user_first_visit AS (
  -- Get first visit date for each user
  SELECT
    user_id,
    MIN(DATE_TRUNC('day', session_start)) AS first_visit_date
  FROM {{ ref('session_summary') }}
  WHERE user_id IS NOT NULL
  GROUP BY user_id
),

user_return_visits AS (
  -- Get subsequent visits by day from first visit
  SELECT
    ss.user_id,
    ufv.first_visit_date,
    DATE_TRUNC('day', ss.session_start) AS visit_date,
    DATE_PART('day', DATE_TRUNC('day', ss.session_start) - ufv.first_visit_date) AS days_since_first_visit,
    DATE_PART('week', DATE_TRUNC('day', ss.session_start) - ufv.first_visit_date) AS weeks_since_first_visit,
    DATE_PART('month', DATE_TRUNC('day', ss.session_start) - ufv.first_visit_date) AS months_since_first_visit,
    SUM(ss.purchase_value) AS revenue
  FROM {{ ref('session_summary') }} ss
  JOIN user_first_visit ufv ON ss.user_id = ufv.user_id
  GROUP BY ss.user_id, ufv.first_visit_date, DATE_TRUNC('day', ss.session_start)
),

cohort_size AS (
  -- Count users in each cohort (by first visit date)
  SELECT
    first_visit_date,
    COUNT(DISTINCT user_id) AS num_users
  FROM user_first_visit
  GROUP BY first_visit_date
)

SELECT
  cs.first_visit_date AS cohort_date,
  cs.num_users AS cohort_size,
  urv.weeks_since_first_visit,
  COUNT(DISTINCT urv.user_id) AS active_users,
  SUM(urv.revenue) AS cohort_revenue,
  COUNT(DISTINCT urv.user_id)::numeric / cs.num_users AS retention_rate
FROM cohort_size cs
LEFT JOIN user_return_visits urv ON cs.first_visit_date = urv.first_visit_date
GROUP BY cs.first_visit_date, cs.num_users, urv.weeks_since_first_visit
ORDER BY cs.first_visit_date, urv.weeks_since_first_visit