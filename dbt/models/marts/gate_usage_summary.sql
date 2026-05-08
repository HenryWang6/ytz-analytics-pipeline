{{
    config(
        materialized='table'
    )
}}

WITH gate_usage AS (
    -- Departures
    SELECT
        gate_dep                            AS gate,
        operating_airline_iata              AS airline_iata,
        dim_airline_name                    AS airline_name,
        'departure'                         AS operation_type
    FROM {{ ref('int_flights_enriched') }}
    WHERE gate_dep IS NOT NULL
      AND carrier_role = 'operating'

    UNION ALL

    -- Arrivals
    SELECT
        gate_arr                            AS gate,
        operating_airline_iata              AS airline_iata,
        dim_airline_name                    AS airline_name,
        'arrival'                           AS operation_type
    FROM {{ ref('int_flights_enriched') }}
    WHERE gate_arr IS NOT NULL
      AND carrier_role = 'operating'
)

SELECT
    gate,
    airline_iata,
    airline_name,
    COUNT_IF(operation_type = 'departure')  AS departure_count,
    COUNT_IF(operation_type = 'arrival')    AS arrival_count,
    COUNT(*)                                AS total_flight_count
FROM gate_usage
GROUP BY gate, airline_iata, airline_name
ORDER BY gate, airline_iata
