{{ config(schema='analytics') }}

SELECT
  product_id,
  COUNT(*) FILTER (WHERE event_type = 'product_view') AS views,
  COUNT(*) FILTER (WHERE event_type = 'add_to_cart') AS adds_to_cart,
  COUNT(*) FILTER (WHERE event_type = 'purchase') AS purchases,
  SUM(value) FILTER (WHERE event_type = 'purchase') AS revenue
FROM {{ ref('stg_events') }}
WHERE product_id IS NOT NULL
GROUP BY product_id
