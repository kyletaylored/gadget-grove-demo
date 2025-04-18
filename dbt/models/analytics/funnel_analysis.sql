{{ config(schema='analytics') }}

WITH funnel_counts AS (
  SELECT
    event_type,
    COUNT(DISTINCT session_id) AS sessions
  FROM {{ ref('stg_events') }}
  WHERE event_type IN ('page_view', 'product_view', 'add_to_cart', 'begin_checkout', 'purchase', 'checkout_error')
  GROUP BY event_type
)

SELECT
  event_type,
  sessions,
  ROUND(100.0 * sessions / NULLIF(FIRST_VALUE(sessions) OVER (ORDER BY CASE event_type
    WHEN 'page_view' THEN 1
    WHEN 'product_view' THEN 2
    WHEN 'add_to_cart' THEN 3
    WHEN 'begin_checkout' THEN 4
    WHEN 'purchase' THEN 5
    WHEN 'checkout_error' THEN 6 END), 1), 2) AS conversion_pct
FROM funnel_counts
