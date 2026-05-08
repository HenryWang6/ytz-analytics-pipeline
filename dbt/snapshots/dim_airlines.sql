{% snapshot dim_airlines %}

{{
    config(
        unique_key='airline_iata',
        strategy='check',
        check_cols=['airline_name', 'airline_icao']
    )
}}

WITH source AS (
    SELECT DISTINCT
        airline_iata,
        airline_name,
        airline_icao
    FROM {{ ref('stg_raw_flights') }}
    WHERE airline_iata IS NOT NULL
),

ranked AS (
    SELECT
        airline_iata,
        airline_name,
        airline_icao,
        ROW_NUMBER() OVER (
            PARTITION BY airline_iata
            ORDER BY
                CASE WHEN airline_name IS NOT NULL THEN 0 ELSE 1 END,
                CASE WHEN airline_icao IS NOT NULL THEN 0 ELSE 1 END
        ) AS rn
    FROM source
)

SELECT
    airline_iata,
    airline_name,
    airline_icao
FROM ranked
WHERE rn = 1

{% endsnapshot %}
