-- models/staging/stg_user_events.sql
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
  -- Extract common properties
  properties->>'name' as user_name,
  properties->>'email' as user_email
FROM {{ source('raw_data', 'user_events') }}