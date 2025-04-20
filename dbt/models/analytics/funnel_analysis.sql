-- models/analytics/funnel_analysis.sql
{{ config(schema='analytics') }}

WITH session_funnel AS (
  SELECT
    session_id,
    MAX(CASE WHEN total_page_views > 0 THEN 1 ELSE 0 END) AS reached_browse,
    MAX(CASE WHEN product_views > 0 THEN 1 ELSE 0 END) AS reached_product,
    MAX(CASE WHEN cart_adds > 0 THEN 1 ELSE 0 END) AS reached_cart,
    MAX(CASE WHEN transaction_id IS NOT NULL THEN 1 ELSE 0 END) AS reached_purchase
  FROM {{ ref('session_summary') }}
  GROUP BY session_id
),

daily_funnel AS (
  SELECT
    DATE_TRUNC('day', ss.session_start) AS event_date,
    COUNT(DISTINCT sf.session_id) AS total_sessions,
    SUM(sf.reached_browse) AS browse_sessions,
    SUM(sf.reached_product) AS product_sessions,
    SUM(sf.reached_cart) AS cart_sessions,
    SUM(sf.reached_purchase) AS purchase_sessions
  FROM session_funnel sf
  JOIN {{ ref('session_summary') }} ss ON sf.session_id = ss.session_id
  GROUP BY DATE_TRUNC('day', ss.session_start)
)

SELECT
  event_date,
  total_sessions,
  browse_sessions,
  product_sessions,
  cart_sessions,
  purchase_sessions,
  -- Conversion rates between stages
  CASE WHEN total_sessions > 0 THEN 
    ROUND(browse_sessions::numeric / total_sessions, 4) 
  ELSE 0 END AS browse_rate,
  CASE WHEN browse_sessions > 0 THEN 
    ROUND(product_sessions::numeric / browse_sessions, 4) 
  ELSE 0 END AS browse_to_product_rate,
  CASE WHEN product_sessions > 0 THEN 
    ROUND(cart_sessions::numeric / product_sessions, 4) 
  ELSE 0 END AS product_to_cart_rate,
  CASE WHEN cart_sessions > 0 THEN 
    ROUND(purchase_sessions::numeric / cart_sessions, 4) 
  ELSE 0 END AS cart_to_purchase_rate,
  -- Overall conversion
  CASE WHEN total_sessions > 0 THEN 
    ROUND(purchase_sessions::numeric / total_sessions, 4) 
  ELSE 0 END AS overall_conversion_rate
FROM daily_funnel
ORDER BY event_date DESC