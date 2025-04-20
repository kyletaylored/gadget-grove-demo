-- models/staging/stg_ecommerce_events.sql
{{ config(schema='staging') }}

SELECT
  id,
  type,
  event,
  timestamp,
  server_timestamp,
  session_id,
  user_id,
  client_ip,
  user_agent,
  properties,
  queue_name,
  processed_timestamp,
  -- Extract common ecommerce properties
  properties->>'product_id' as product_id,
  properties->>'name' as product_name,
  properties->>'brand' as product_brand,
  properties->>'category' as product_category,
  (properties->>'price')::numeric as product_price,
  (properties->>'quantity')::int as quantity,
  (properties->>'value')::numeric as value,
  properties->>'transaction_id' as transaction_id,
  properties->>'error' as error_reason
FROM {{ source('raw_data', 'ecommerce_events') }}