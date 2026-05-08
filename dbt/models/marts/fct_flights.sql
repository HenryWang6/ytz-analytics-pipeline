{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='flight_id',
        merge_update_columns=[
            'flight_status', 'actual_dep', 'actual_arr',
            'delay_dep', 'delay_arr', 'is_on_time_dep', 'is_on_time_arr',
            'delay_bucket_dep', 'delay_bucket_arr', 'is_cancelled',
            'actual_operation_date', 'actual_year', 'actual_month',
            'actual_day_name', 'actual_is_weekend'
        ],
        on_schema_change='fail'
    )
}}

SELECT
    flight_id,
    flight_date,
    direction,
    flight_status,
    dep_iata,
    dep_airport_name,
    arr_iata,
    arr_airport_name,
    airline_iata,
    airline_name,
    airline_icao,
    flight_iata,
    operating_airline_iata,
    operating_flight_iata,
    sched_dep,
    sched_arr,
    actual_dep,
    actual_arr,
    delay_dep,
    delay_arr,
    gate_dep,
    gate_arr,
    baggage,
    terminal_dep,
    terminal_arr,
    aircraft_icao24,
    extracted_at,
    target_airport,

    -- Dimension enrichments
    dim_airline_name,
    dim_airline_icao,
    dim_dep_airport_name,
    dim_arr_airport_name,

    -- Scheduled date attributes
    sched_year,
    sched_month,
    sched_day_name,
    sched_is_weekend,

    -- Pre-computed derived columns
    actual_operation_date,
    is_on_time_dep,
    is_on_time_arr,
    delay_bucket_dep,
    delay_bucket_arr,
    is_cancelled,

    -- Actual operation date attributes
    actual_year,
    actual_month,
    actual_day_name,
    actual_is_weekend

FROM {{ ref('int_flights_enriched') }}
WHERE carrier_role = 'operating'

{% if is_incremental() %}
  -- 3-day look-back: re-process recent flights to catch status transitions
  -- (e.g., scheduled -> active -> landed across consecutive extracts)
  AND flight_date >= (SELECT MAX(flight_date) FROM {{ this }}) - INTERVAL '3 days'
{% endif %}
