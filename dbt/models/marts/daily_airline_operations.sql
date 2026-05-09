{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='actual_operation_date, airline_iata',
        on_schema_change='fail'
    )
}}

SELECT
    actual_operation_date,
    airline_iata,
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
FROM {{ ref('int_flights_enriched') }}
WHERE actual_operation_date IS NOT NULL
  AND airline_iata IS NOT NULL

{% if is_incremental() %}
  AND actual_operation_date >= (SELECT MAX(actual_operation_date) FROM {{ this }}) - INTERVAL '7 days'
{% endif %}

GROUP BY actual_operation_date, airline_iata
ORDER BY actual_operation_date, airline_iata
