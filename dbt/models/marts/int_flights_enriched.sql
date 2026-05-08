{{
    config(
        materialized='table'
    )
}}

WITH stg AS (
    SELECT * FROM {{ ref('stg_raw_flights') }}
),

enriched AS (
    SELECT
        stg.*,

        -- Dimension: airline (current SCD2 version only)
        al.airline_name                       AS dim_airline_name,
        al.airline_icao                       AS dim_airline_icao,

        -- Dimension: departure airport (current SCD2 version only)
        dep_apt.airport_name                  AS dim_dep_airport_name,

        -- Dimension: arrival airport (current SCD2 version only)
        arr_apt.airport_name                  AS dim_arr_airport_name,

        -- Dimension: scheduled date attributes
        sched_date_dim.year                   AS sched_year,
        sched_date_dim.month                  AS sched_month,
        sched_date_dim.day_name               AS sched_day_name,
        sched_date_dim.is_weekend             AS sched_is_weekend,

        -- Pre-computed: actual operation date (used in next JOIN)
        COALESCE(
            DATE(stg.actual_dep),
            DATE(stg.actual_arr)
        )                                     AS actual_operation_date,

        -- Pre-computed: on-time departure
        IFF(
            stg.delay_dep <= 15 AND stg.actual_dep IS NOT NULL,
            TRUE,
            IFF(stg.actual_dep IS NULL, NULL, FALSE)
        )                                     AS is_on_time_dep,

        -- Pre-computed: on-time arrival
        IFF(
            stg.delay_arr <= 15 AND stg.actual_arr IS NOT NULL,
            TRUE,
            IFF(stg.actual_arr IS NULL, NULL, FALSE)
        )                                     AS is_on_time_arr,

        -- Pre-computed: departure delay bucket
        CASE
            WHEN stg.actual_dep IS NULL THEN NULL
            WHEN stg.delay_dep <= 15 THEN 'On Time'
            WHEN stg.delay_dep <= 30 THEN '15-30 min'
            WHEN stg.delay_dep <= 60 THEN '30-60 min'
            ELSE '60+ min'
        END                                   AS delay_bucket_dep,

        -- Pre-computed: arrival delay bucket
        CASE
            WHEN stg.actual_arr IS NULL THEN NULL
            WHEN stg.delay_arr <= 15 THEN 'On Time'
            WHEN stg.delay_arr <= 30 THEN '15-30 min'
            WHEN stg.delay_arr <= 60 THEN '30-60 min'
            ELSE '60+ min'
        END                                   AS delay_bucket_arr,

        -- Pre-computed: cancellation flag
        IFF(
            LOWER(stg.flight_status) IN ('cancelled', 'canceled'),
            TRUE,
            FALSE
        )                                     AS is_cancelled

    FROM stg
    LEFT JOIN {{ ref('dim_airlines') }} AS al
        ON stg.airline_iata = al.airline_iata
        AND al.dbt_valid_to IS NULL
    LEFT JOIN {{ ref('dim_airports') }} AS dep_apt
        ON stg.dep_iata = dep_apt.airport_iata
        AND dep_apt.dbt_valid_to IS NULL
    LEFT JOIN {{ ref('dim_airports') }} AS arr_apt
        ON stg.arr_iata = arr_apt.airport_iata
        AND arr_apt.dbt_valid_to IS NULL
    LEFT JOIN {{ ref('dim_dates') }} AS sched_date_dim
        ON stg.flight_date = sched_date_dim.date_id
)

SELECT
    enriched.*,

    -- Dimension: actual operation date attributes
    actual_date_dim.year                   AS actual_year,
    actual_date_dim.month                  AS actual_month,
    actual_date_dim.day_name               AS actual_day_name,
    actual_date_dim.is_weekend             AS actual_is_weekend

FROM enriched
LEFT JOIN {{ ref('dim_dates') }} AS actual_date_dim
    ON enriched.actual_operation_date = actual_date_dim.date_id
