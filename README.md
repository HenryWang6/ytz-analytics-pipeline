# YTZ Analytics Pipeline

A production-grade aviation data pipeline — API extraction to dbt-modeled analytics in Snowflake — built to demonstrate end-to-end analytics engineering with testing, documentation, and CI/CD.

The pipeline targets daily arriving and departing flights for Toronto Island Airport (YTZ), taking advantage of the airport's low volume to capture a full daily snapshot without exceeding free-tier API limits.

---

## Architecture & Design Choices

### 1. Decoupled ELT
Extraction and loading are strictly separated:
- **Extract (`src/extract_flights.py`)**: Fetches data from the AviationStack API, handles pagination, buffers raw NDJSON to `data/`
- **Load (`src/load_flights.py`)**: Scans `data/`, uploads to Snowflake internal stage, executes `COPY INTO`

If the Snowflake connection fails, the API quota isn't wasted — JSON files remain safely stored for the next attempt.

### 2. Schema-on-Read (VARIANT)
The target table (`RAW_DB.AVIATION.RAW_FLIGHTS`) stores raw JSON in a `VARIANT` column. All schema parsing and transformations happen downstream in dbt.

### 3. dbt Transformation Layer
Staging models flatten the raw JSON into typed columns. Marts expose business-facing fact and dimension tables. Testing uses dbt schema tests (unique, not_null) and dbt-expectations.

### 4. OOP + Centralized Config
Core logic in classes (`AviationAPIClient`, `SnowflakeLoader`) with `main()` entry points. All environment variables, paths, and defaults in `src/config.py`.

### 5. Testing
- **pytest** — unit tests for Python pipeline code (API calls mocked, zero quota consumed)
- **dbt tests** — schema tests + dbt-expectations for data quality
- **dbt-expectations** — extended assertions beyond built-in tests

---

## File Structure

```text
ytz-analytics-pipeline/
├── src/
│   ├── config.py              # Centralized config, env loading, logger
│   ├── extract_flights.py     # AviationAPIClient + extraction orchestration
│   └── load_flights.py        # SnowflakeLoader + file ingestion
├── dbt/
│   ├── models/staging/        # 1:1 with source, JSON flattening
│   ├── models/marts/          # Business-facing fact/dimension tables
│   ├── macros/                # Reusable Jinja macros
│   ├── seeds/                 # CSV reference data
│   ├── snapshots/             # SCD Type 2 (planned)
│   └── tests/                 # Custom singular data tests
├── tests/                     # pytest unit tests
├── data/                      # Local NDJSON buffer (extract → load handoff)
├── setup_snowflake.sql        # DDL: database, schema, stage, table
├── requirements.txt           # Python dependencies
├── .env                       # Local credentials (git-ignored)
└── .github/workflows/         # CI/CD: daily extraction at 02:00 UTC
```

---

## Execution & Deployment

### Local Development
```bash
pip install -r requirements.txt
python src/extract_flights.py   # Fetch today's flights from API
python src/load_flights.py      # Load buffered files into Snowflake
```

### dbt
```bash
cd dbt
dbt deps                        # Install dbt packages
dbt debug                       # Verify Snowflake connection
dbt run                         # Build models
dbt test                        # Run data quality tests
```

### Testing (no API calls)
```bash
python -m pytest tests/ -v
```

### CI/CD (GitHub Actions)
The `.github/workflows/daily_flight_extract.yml` workflow runs daily at 02:00 UTC. Add your `.env` variables as GitHub Repository Secrets.
