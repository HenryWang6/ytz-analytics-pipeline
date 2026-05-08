{% snapshot dim_airports %}

{{
    config(
        unique_key='airport_iata',
        strategy='check',
        check_cols=['airport_name']
    )
}}

WITH source AS (
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
),

ranked AS (
    SELECT
        airport_iata,
        airport_name,
        ROW_NUMBER() OVER (
            PARTITION BY airport_iata
            ORDER BY CASE WHEN airport_name IS NOT NULL THEN 0 ELSE 1 END
        ) AS rn
    FROM source
)

SELECT
    airport_iata,
    airport_name
FROM ranked
WHERE rn = 1

{% endsnapshot %}
