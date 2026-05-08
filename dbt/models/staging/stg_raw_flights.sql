WITH unpacked AS (
    SELECT
        s.EXTRACTED_AT                                                                     AS extracted_at,
        s.DIRECTION                                                                     AS direction,
        s.TARGET_AIRPORT                                                                AS target_airport,

        -- Top-level JSON fields
        s.RAW_JSON:flight_date::DATE                                                    AS flight_date,
        s.RAW_JSON:flight_status::VARCHAR                                               AS flight_status,

        -- Departure fields
        s.RAW_JSON:departure.iata::VARCHAR                                              AS dep_iata,
        s.RAW_JSON:departure.airport::VARCHAR                                           AS dep_airport_name,
        TRY_TO_TIMESTAMP_TZ(s.RAW_JSON:departure.scheduled::VARCHAR)                    AS sched_dep,
        TRY_TO_TIMESTAMP_TZ(s.RAW_JSON:departure.actual::VARCHAR)                       AS actual_dep,
        s.RAW_JSON:departure.delay::INT                                                 AS delay_dep,
        s.RAW_JSON:departure.gate::VARCHAR                                              AS gate_dep,
        s.RAW_JSON:departure.terminal::VARCHAR                                          AS terminal_dep,

        -- Arrival fields
        s.RAW_JSON:arrival.iata::VARCHAR                                                AS arr_iata,
        s.RAW_JSON:arrival.airport::VARCHAR                                             AS arr_airport_name,
        TRY_TO_TIMESTAMP_TZ(s.RAW_JSON:arrival.scheduled::VARCHAR)                      AS sched_arr,
        TRY_TO_TIMESTAMP_TZ(s.RAW_JSON:arrival.actual::VARCHAR)                         AS actual_arr,
        s.RAW_JSON:arrival.delay::INT                                                   AS delay_arr,
        s.RAW_JSON:arrival.gate::VARCHAR                                                AS gate_arr,
        s.RAW_JSON:arrival.terminal::VARCHAR                                            AS terminal_arr,
        s.RAW_JSON:arrival.baggage::VARCHAR                                             AS baggage,

        -- Airline fields (marketing carrier — who sells the ticket)
        s.RAW_JSON:airline.iata::VARCHAR                                                AS airline_iata,
        s.RAW_JSON:airline.name::VARCHAR                                                AS airline_name,
        s.RAW_JSON:airline.icao::VARCHAR                                                AS airline_icao,

        -- Flight number (marketing carrier's flight number)
        s.RAW_JSON:flight.iata::VARCHAR                                                 AS flight_iata,

        -- Codeshare: operating carrier details (null when this airline IS the operator)
        UPPER(s.RAW_JSON:flight.codeshared:airline_iata::VARCHAR)                       AS codeshare_airline_iata,
        UPPER(s.RAW_JSON:flight.codeshared:flight_iata::VARCHAR)                        AS codeshare_flight_iata,

        -- Aircraft
        s.RAW_JSON:aircraft.icao24::VARCHAR                                             AS aircraft_icao24

    FROM {{ source('raw', 'raw_flights') }} AS s
),

derived AS (
    SELECT
        unpacked.*,

        IFF(unpacked.codeshare_airline_iata IS NOT NULL, 'marketing', 'operating')      AS carrier_role,

        COALESCE(unpacked.codeshare_airline_iata, unpacked.airline_iata)                 AS operating_airline_iata,

        COALESCE(unpacked.codeshare_flight_iata, unpacked.flight_iata)                   AS operating_flight_iata

    FROM unpacked
)

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'derived.flight_date',
        'derived.operating_flight_iata',
        'derived.direction'
    ]) }}                                                                               AS flight_id,

    derived.flight_date,
    derived.direction,
    derived.flight_status,
    derived.dep_iata,
    derived.dep_airport_name,
    derived.arr_iata,
    derived.arr_airport_name,
    derived.airline_iata,
    derived.airline_name,
    derived.airline_icao,
    derived.flight_iata,
    derived.carrier_role,
    derived.operating_airline_iata,
    derived.operating_flight_iata,
    derived.sched_dep,
    derived.sched_arr,
    derived.actual_dep,
    derived.actual_arr,
    derived.delay_dep,
    derived.delay_arr,
    derived.gate_dep,
    derived.gate_arr,
    derived.baggage,
    derived.terminal_dep,
    derived.terminal_arr,
    derived.aircraft_icao24,
    derived.extracted_at,
    derived.target_airport

FROM derived
