{% snapshot dim_airports %}

{{
    config(
        unique_key='airport_iata',
        strategy='check',
        check_cols=['airport_name']
    )
}}

SELECT DISTINCT
    dep_iata AS airport_iata,
    dep_airport_name AS airport_name
FROM {{ ref('stg_raw_flights') }}
WHERE dep_iata IS NOT NULL

UNION

SELECT DISTINCT
    arr_iata AS airport_iata,
    arr_airport_name AS airport_name
FROM {{ ref('stg_raw_flights') }}
WHERE arr_iata IS NOT NULL

{% endsnapshot %}
