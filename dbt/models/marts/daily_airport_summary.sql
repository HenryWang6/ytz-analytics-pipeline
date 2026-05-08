{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='flight_date',
        on_schema_change='fail'
    )
}}

SELECT
    flight_date,
    COUNT(*)                                                                                  AS total_scheduled,
    COUNT_IF(flight_status NOT IN ('cancelled', 'canceled'))                                  AS total_actual,
    COUNT_IF(direction = 'DEPARTURE')                                                         AS scheduled_dep,
    COUNT_IF(direction = 'ARRIVAL')                                                           AS scheduled_arr,
    COUNT_IF(direction = 'DEPARTURE' AND flight_status NOT IN ('cancelled', 'canceled'))      AS actual_dep,
    COUNT_IF(direction = 'ARRIVAL' AND flight_status NOT IN ('cancelled', 'canceled'))        AS actual_arr,
    COUNT_IF(direction = 'DEPARTURE' AND is_on_time_dep = TRUE)                               AS on_time_dep,
    COUNT_IF(direction = 'ARRIVAL' AND is_on_time_arr = TRUE)                                 AS on_time_arr,
    COUNT_IF(is_cancelled = TRUE)                                                             AS cancelled_count,
    ROUND(
        COUNT_IF(direction = 'DEPARTURE' AND is_on_time_dep = TRUE) * 100.0
        / NULLIF(COUNT_IF(direction = 'DEPARTURE' AND actual_dep IS NOT NULL), 0), 2
    )                                                                                         AS dep_otp_pct,
    ROUND(
        COUNT_IF(direction = 'ARRIVAL' AND is_on_time_arr = TRUE) * 100.0
        / NULLIF(COUNT_IF(direction = 'ARRIVAL' AND actual_arr IS NOT NULL), 0), 2
    )                                                                                         AS arr_otp_pct,
    ROUND(
        COUNT_IF(is_cancelled = TRUE) * 100.0
        / NULLIF(COUNT(*), 0), 2
    )                                                                                         AS cancellation_rate_pct
FROM {{ ref('fct_flights') }}

{% if is_incremental() %}
  WHERE flight_date >= (SELECT MAX(flight_date) FROM {{ this }}) - INTERVAL '7 days'
{% endif %}

GROUP BY flight_date
ORDER BY flight_date
