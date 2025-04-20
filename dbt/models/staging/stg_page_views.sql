-- models/staging/stg_page_views.sql
{{ config(schema='staging') }}

SELECT
  id,
  type,
  timestamp,
  server_timestamp,
  session_id,
  user_id,
  client_ip,
  user_agent,
  url,
  path,
  properties,
  queue_name,
  processed_timestamp
FROM {{ source('raw_data', 'page_views') }}