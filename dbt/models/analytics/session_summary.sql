{{ config(schema='analytics') }}

WITH ordered_events AS (
  SELECT
    session_id,
    event_type,
    event_timestamp,
    value,
    ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY event_timestamp ASC) AS event_rank
  FROM {{ ref('stg_events') }}
),

session_agg AS (
  SELECT
    session_id,
    MIN(event_timestamp) AS session_start,
    MAX(event_timestamp) AS session_end,
    MAX(CASE WHEN event_type = 'purchase' THEN value END) AS total_spent,
    COUNT(*) AS total_events,
    MAX(event_type) FILTER (WHERE event_type = 'purchase') AS did_purchase,
    MAX(event_type) FILTER (WHERE event_type = 'checkout_error') AS had_error
  FROM {{ ref('stg_events') }}
  GROUP BY session_id
)

SELECT
  session_id,
  session_start,
  session_end,
  EXTRACT(EPOCH FROM session_end - session_start) AS session_duration_sec,
  total_spent,
  total_events,
  CASE
    WHEN did_purchase IS NOT NULL THEN 'purchase'
    WHEN had_error IS NOT NULL THEN 'checkout_error'
    ELSE 'abandoned'
  END AS session_status
FROM session_agg
