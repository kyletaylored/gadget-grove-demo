-- models/analytics/daily_metrics.sql
{{ config(schema='analytics') }}

WITH daily_events AS (
  -- Page view metrics
  SELECT
    DATE_TRUNC('day', timestamp) AS event_date,
    COUNT(DISTINCT session_id) AS sessions,
    COUNT(*) AS page_views,
    COUNT(*) / COUNT(DISTINCT session_id)::numeric AS pages_per_session
  FROM {{ ref('stg_page_views') }}
  GROUP BY DATE_TRUNC('day', timestamp)
),

daily_commerce AS (
  -- E-commerce metrics
  SELECT
    DATE_TRUNC('day', timestamp) AS event_date,
    COUNT(*) FILTER (WHERE event = 'product_view') AS product_views,
    COUNT(*) FILTER (WHERE event = 'add_to_cart') AS add_to_cart_events,
    COUNT(*) FILTER (WHERE event = 'purchase') AS purchase_events,
    COUNT(DISTINCT session_id) FILTER (WHERE event = 'purchase') AS purchasing_sessions,
    SUM(value) FILTER (WHERE event = 'purchase') AS total_revenue,
    SUM(value) FILTER (WHERE event = 'purchase') / 
      NULLIF(COUNT(DISTINCT session_id) FILTER (WHERE event = 'purchase'), 0) AS average_order_value
  FROM {{ ref('stg_ecommerce_events') }}
  GROUP BY DATE_TRUNC('day', timestamp)
),

conversion_rates AS (
  -- Session outcomes for conversion rate calculation
  SELECT
    DATE_TRUNC('day', session_start) AS event_date,
    COUNT(*) AS total_sessions,
    COUNT(*) FILTER (WHERE session_outcome = 'purchase') AS purchase_sessions,
    COUNT(*) FILTER (WHERE session_outcome = 'checkout_error') AS error_sessions,
    COUNT(*) FILTER (WHERE session_outcome = 'cart_abandonment') AS cart_abandonment_sessions,
    COUNT(*) FILTER (WHERE session_outcome = 'browse_only') AS browse_only_sessions,
    COUNT(*) FILTER (WHERE session_outcome = 'bounce') AS bounce_sessions
  FROM {{ ref('session_summary') }}
  GROUP BY DATE_TRUNC('day', session_start)
)

SELECT
  COALESCE(de.event_date, dc.event_date, cr.event_date) AS event_date,
  -- Page metrics
  de.sessions,
  de.page_views,
  de.pages_per_session,
  -- E-commerce metrics
  dc.product_views,
  dc.add_to_cart_events,
  dc.purchase_events,
  dc.purchasing_sessions,
  dc.total_revenue,
  dc.average_order_value,
  -- Conversion metrics
  cr.total_sessions,
  CASE 
    WHEN cr.total_sessions > 0 THEN 
      ROUND(cr.purchase_sessions::numeric / cr.total_sessions, 4)
    ELSE 0
  END AS conversion_rate,
  CASE 
    WHEN cr.total_sessions > 0 THEN 
      ROUND(cr.bounce_sessions::numeric / cr.total_sessions, 4)
    ELSE 0
  END AS bounce_rate,
  CASE 
    WHEN dc.add_to_cart_events > 0 THEN 
      ROUND(dc.purchase_events::numeric / dc.add_to_cart_events, 4)
    ELSE 0
  END AS cart_to_purchase_rate
FROM daily_events de
FULL OUTER JOIN daily_commerce dc ON de.event_date = dc.event_date
FULL OUTER JOIN conversion_rates cr ON de.event_date = cr.event_date
ORDER BY event_date DESC