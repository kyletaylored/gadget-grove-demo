{{ config(schema='staging') }}

SELECT
  session_id,
  event_type,
  CAST(timestamp AS timestamp) AS event_timestamp,
  path,
  product_id,
  CAST(value AS numeric) AS value,
  transaction_id,
  reason
FROM {{ source('raw_data', 'events') }}
