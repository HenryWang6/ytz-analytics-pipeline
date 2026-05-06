-- 1. Check the total number of records loaded today and split by direction
SELECT 
    DIRECTION, 
    COUNT(*) as record_count 
FROM RAW_DB.AVIATION.RAW_FLIGHTS 
WHERE DATE(EXTRACTED_AT) = CURRENT_DATE()
GROUP BY DIRECTION;

-- 2. Check the extraction timestamps to see if the pipeline ran multiple times today
-- If you see multiple distinct timestamps for the same direction, the pipeline likely ran twice.
SELECT 
    EXTRACTED_AT,
    DIRECTION, 
    COUNT(*) as record_count 
FROM RAW_DB.AVIATION.RAW_FLIGHTS 
WHERE DATE(EXTRACTED_AT) = CURRENT_DATE()
GROUP BY EXTRACTED_AT, DIRECTION
ORDER BY EXTRACTED_AT DESC;

-- 3. Identify duplicate flights loaded today based on flight date and flight IATA
-- This unpacks the JSON to see if specific flights are duplicated.
SELECT 
    RAW_JSON:flight_date::VARCHAR AS flight_date,
    RAW_JSON:flight:iata::VARCHAR AS flight_iata,
    DIRECTION,
    COUNT(*) as frequency
FROM RAW_DB.AVIATION.RAW_FLIGHTS 
WHERE DATE(EXTRACTED_AT) = CURRENT_DATE()
GROUP BY 1, 2, 3
HAVING COUNT(*) > 1
ORDER BY frequency DESC;

-- 4. View the specific RAW_JSON details for a duplicated flight
-- If query 3 finds duplicates, replace 'ENTER_FLIGHT_IATA_HERE' with a flight number (e.g., 'PD456') to inspect differences.
SELECT 
    EXTRACTED_AT,
    RAW_JSON:flight_status::VARCHAR AS flight_status,
    RAW_JSON
FROM RAW_DB.AVIATION.RAW_FLIGHTS 
WHERE DATE(EXTRACTED_AT) = CURRENT_DATE()
  AND RAW_JSON:flight:iata::VARCHAR = 'ENTER_FLIGHT_IATA_HERE'
ORDER BY EXTRACTED_AT DESC;
