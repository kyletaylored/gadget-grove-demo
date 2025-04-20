-- models/analytics/product_performance.sql
{{ config(schema='analytics') }}

WITH product_events AS (
  SELECT
    product_id,
    product_name,
    product_brand,
    product_category,
    product_price,
    event,
    value,
    timestamp,
    session_id
  FROM {{ ref('stg_ecommerce_events') }}
  WHERE product_id IS NOT NULL
)

SELECT
  product_id,
  MAX(product_name) AS product_name,
  MAX(product_brand) AS product_brand,
  MAX(product_category) AS product_category,
  MAX(product_price) AS product_price,
  COUNT(*) AS total_events,
  COUNT(*) FILTER (WHERE event = 'product_view') AS views,
  COUNT(*) FILTER (WHERE event = 'add_to_cart') AS adds_to_cart,
  COUNT(*) FILTER (WHERE event = 'purchase') AS purchases,
  COUNT(DISTINCT session_id) FILTER (WHERE event = 'product_view') AS unique_view_sessions,
  COUNT(DISTINCT session_id) FILTER (WHERE event = 'add_to_cart') AS unique_cart_sessions,
  COUNT(DISTINCT session_id) FILTER (WHERE event = 'purchase') AS unique_purchase_sessions,
  SUM(value) FILTER (WHERE event = 'purchase') AS total_revenue,
  CASE 
    WHEN COUNT(*) FILTER (WHERE event = 'product_view') > 0 THEN
      ROUND(COUNT(*) FILTER (WHERE event = 'add_to_cart')::numeric / 
            COUNT(*) FILTER (WHERE event = 'product_view'), 4)
    ELSE 0
  END AS view_to_cart_rate,
  CASE 
    WHEN COUNT(*) FILTER (WHERE event = 'add_to_cart') > 0 THEN
      ROUND(COUNT(*) FILTER (WHERE event = 'purchase')::numeric / 
            COUNT(*) FILTER (WHERE event = 'add_to_cart'), 4)
    ELSE 0
  END AS cart_to_purchase_rate
FROM product_events
GROUP BY product_id