WITH date_spine AS (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2024-01-01' as date)",
        end_date="cast('2030-12-31' as date)"
    ) }}
),

enriched AS (
    SELECT
        date_day                                                                          AS date_id,
        date_day,
        EXTRACT(YEAR FROM date_day)                                                       AS year,
        EXTRACT(MONTH FROM date_day)                                                      AS month,
        EXTRACT(DAY FROM date_day)                                                        AS day,
        EXTRACT(QUARTER FROM date_day)                                                    AS quarter,
        EXTRACT(DAYOFWEEK FROM date_day)                                                  AS day_of_week,
        EXTRACT(DAYOFYEAR FROM date_day)                                                  AS day_of_year,
        EXTRACT(WEEK FROM date_day)                                                       AS week_of_year,
        TO_VARCHAR(date_day, 'Month')                                                     AS month_name,
        TO_VARCHAR(date_day, 'Day')                                                       AS day_name,
        IFF(EXTRACT(DAYOFWEEK FROM date_day) IN (6, 7), TRUE, FALSE)                      AS is_weekend,
        TO_VARCHAR(date_day, 'YYYY-MM')                                                   AS year_month
    FROM date_spine
)

SELECT * FROM enriched
