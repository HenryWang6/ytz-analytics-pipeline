{% snapshot dim_airlines %}

{{
    config(
        unique_key='airline_iata',
        strategy='check',
        check_cols=['airline_name', 'airline_icao']
    )
}}

SELECT DISTINCT
    airline_iata,
    airline_name,
    airline_icao
FROM {{ ref('stg_raw_flights') }}
WHERE airline_iata IS NOT NULL

{% endsnapshot %}
