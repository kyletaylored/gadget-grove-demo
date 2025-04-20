-- models/staging/stg_analytics_events.sql
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
  processed_timestamp
FROM {{ source('raw_data', 'analytics_events') }}