-- Run these commands in your Snowflake worksheet to set up the environment.

-- 1. Use the appropriate role and warehouse (as defined in your .env)
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;

-- 2. Create the Database
CREATE DATABASE IF NOT EXISTS RAW_DB;

-- 3. Create the Schema
CREATE SCHEMA IF NOT EXISTS RAW_DB.AVIATION;

-- 4. Use the newly created Database and Schema
USE DATABASE RAW_DB;
USE SCHEMA AVIATION;

-- 5. Create the Internal Stage
-- This is where the Python script will PUT the temporary JSON file before copying it into the table.
CREATE STAGE IF NOT EXISTS RAW_DB.AVIATION.AVIATION_STAGE
  FILE_FORMAT = (TYPE = JSON);

-- 6. Create the Target Table
-- Using a VARIANT column for RAW_JSON to support flexible ELT querying.
CREATE OR REPLACE TABLE RAW_DB.AVIATION.RAW_FLIGHTS (
    RAW_JSON VARIANT,
    EXTRACTED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    DIRECTION VARCHAR,
    TARGET_AIRPORT VARCHAR
);

-- Note: The Python script will handle uploading to the stage and running the COPY INTO command.
