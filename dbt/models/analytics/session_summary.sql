-- models/analytics/session_summary.sql
{{ config(schema='analytics') }}

WITH page_views AS (
  SELECT
    session_id,
    MIN(timestamp) AS first_page_view,
    MAX(timestamp) AS last_page_view,
    COUNT(*) AS total_page_views,
    ARRAY_AGG(DISTINCT path) AS viewed_pages
  FROM {{ ref('stg_page_views') }}
  GROUP BY session_id
),

user_data AS (
  SELECT
    session_id,
    MAX(user_id) AS user_id,
    MAX(user_name) AS user_name,
    MAX(user_email) AS user_email,
    MAX(CASE WHEN event = 'identify' THEN 1 ELSE 0 END) AS was_identified
  FROM {{ ref('stg_user_events') }}
  GROUP BY session_id
),

ecommerce_events AS (
  SELECT
    session_id,
    COUNT(*) FILTER (WHERE event = 'product_view') AS product_views,
    COUNT(DISTINCT product_id) FILTER (WHERE event = 'product_view') AS unique_products_viewed,
    COUNT(*) FILTER (WHERE event = 'add_to_cart') AS cart_adds,
    COUNT(DISTINCT product_id) FILTER (WHERE event = 'add_to_cart') AS unique_products_carted,
    MAX(CASE WHEN event = 'purchase' THEN transaction_id END) AS transaction_id,
    MAX(CASE WHEN event = 'purchase' THEN value END) AS purchase_value,
    MAX(CASE WHEN event = 'checkout_error' THEN error_reason END) AS checkout_error
  FROM {{ ref('stg_ecommerce_events') }}
  GROUP BY session_id
)

SELECT
  pv.session_id,
  ud.user_id,
  ud.user_name,
  ud.user_email,
  pv.first_page_view AS session_start,
  pv.last_page_view AS session_end,
  EXTRACT(EPOCH FROM (pv.last_page_view - pv.first_page_view)) AS session_duration_sec,
  pv.total_page_views,
  pv.viewed_pages,
  ud.was_identified,
  ee.product_views,
  ee.unique_products_viewed,
  ee.cart_adds,
  ee.unique_products_carted,
  ee.transaction_id,
  ee.purchase_value,
  ee.checkout_error,
  CASE
    WHEN ee.transaction_id IS NOT NULL THEN 'purchase'
    WHEN ee.checkout_error IS NOT NULL THEN 'checkout_error'
    WHEN ee.cart_adds > 0 THEN 'cart_abandonment'
    WHEN ee.product_views > 0 THEN 'browse_only'
    ELSE 'bounce'
  END AS session_outcome
FROM page_views pv
LEFT JOIN user_data ud ON pv.session_id = ud.session_id
LEFT JOIN ecommerce_events ee ON pv.session_id = ee.session_id