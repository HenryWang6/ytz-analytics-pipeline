WITH unpacked AS (
    SELECT
        -- Metadata
        s.EXTRACTED_AT                                                                  AS extracted_at,
        s.DIRECTION                                                                     AS direction,
        s.TARGET_AIRPORT                                                                AS target_airport,

        -- Flight fields
        s.RAW_JSON:flight_date::DATE                                                    AS flight_date,
        s.RAW_JSON:flight_status::VARCHAR                                               AS flight_status,
        s.RAW_JSON:flight.iata::VARCHAR                                                 AS flight_iata,
        s.RAW_JSON:flight.icao::VARCHAR                                                 AS flight_icao,
        s.RAW_JSON:flight.number::VARCHAR                                               AS flight_number,
        s.RAW_JSON:flight.codeshared                                                    AS flight_codeshared,

        -- Departure fields
        s.RAW_JSON:departure.iata::VARCHAR                                              AS dep_airport_iata,
        s.RAW_JSON:departure.icao::VARCHAR                                              AS dep_airport_icao,
        s.RAW_JSON:departure.airport::VARCHAR                                           AS dep_airport_name,
        TRY_TO_TIMESTAMP_TZ(s.RAW_JSON:departure.scheduled::VARCHAR)                    AS dep_sched_at,
        TRY_TO_TIMESTAMP_TZ(s.RAW_JSON:departure.actual::VARCHAR)                       AS dep_actual_at,
        s.RAW_JSON:departure.terminal::VARCHAR                                          AS dep_terminal,
        s.RAW_JSON:departure.gate::VARCHAR                                              AS dep_gate,
        s.RAW_JSON:departure.timezone::VARCHAR                                          AS dep_timezone,

        -- Arrival fields
        s.RAW_JSON:arrival.iata::VARCHAR                                                AS arr_airport_iata,
        s.RAW_JSON:arrival.icao::VARCHAR                                                AS arr_airport_icao,
        s.RAW_JSON:arrival.airport::VARCHAR                                             AS arr_airport_name,
        TRY_TO_TIMESTAMP_TZ(s.RAW_JSON:arrival.scheduled::VARCHAR)                      AS arr_sched_at,
        TRY_TO_TIMESTAMP_TZ(s.RAW_JSON:arrival.actual::VARCHAR)                         AS arr_actual_at,
        s.RAW_JSON:arrival.terminal::VARCHAR                                            AS arr_terminal,
        s.RAW_JSON:arrival.gate::VARCHAR                                                AS arr_gate,
        s.RAW_JSON:arrival.baggage::VARCHAR                                             AS arr_baggage,
        s.RAW_JSON:arrival.timezone::VARCHAR                                            AS arr_timezone,

        -- Airline fields
        s.RAW_JSON:airline.iata::VARCHAR                                                AS airline_iata,
        s.RAW_JSON:airline.icao::VARCHAR                                                AS airline_icao,
        s.RAW_JSON:airline.name::VARCHAR                                                AS airline_name,

        -- Aircraft
        s.RAW_JSON:aircraft.icao24::VARCHAR                                             AS aircraft_icao24

    FROM {{ source('raw', 'raw_flights') }} AS s
),

derived AS (
    SELECT
        unpacked.*,

        iff(unpacked.flight_codeshared IS NULL, 'operating', 'marketing')                 AS carrier_role,
        COALESCE(unpacked.flight_codeshared:airline_iata::VARCHAR, unpacked.airline_iata)  AS operating_airline_iata,
        COALESCE(unpacked.flight_codeshared:flight_iata::VARCHAR, unpacked.flight_iata)    AS operating_flight_iata
    FROM unpacked
)

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'flight_date',
        'operating_flight_iata',
        'direction'
    ])
    }} AS flight_id,

    derived.*
FROM derived