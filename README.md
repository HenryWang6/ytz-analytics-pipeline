# YTZ Analytics Pipeline

A production-grade aviation data pipeline — API extraction to dbt-modeled analytics in Snowflake — built to demonstrate end-to-end analytics engineering with testing, documentation, and CI/CD.

The pipeline targets arriving and departing flights for Toronto Island Airport (YTZ) on a tri-weekly cadence (Mon/Wed/Fri), capturing complete daily snapshots while staying well within free-tier API limits (~26 of 100 monthly requests).

---

## Architecture & Design Choices

### 1. Decoupled ELT
Extraction and loading are strictly separated:
- **Extract (`src/extract_flights.py`)**: Fetches data from the AviationStack API, client-side date filtering, pagination capped at 1 page (100 records), buffers raw NDJSON to `data/`
- **Load (`src/load_flights.py`)**: Scans `data/`, uploads to Snowflake internal stage, executes `COPY INTO`

After a successful load, files are archived to `data/archive/` to prevent re-loading duplicates. If the Snowflake connection fails, the files remain in `data/` for the next attempt.

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
│   ├── models/staging/        # stg_raw_flights (view) — JSON flattening + codeshare logic
│   ├── models/marts/          # fct_flights + dim/summary models (in progress)
│   ├── models/sources.yml     # Source definition: raw.raw_flights
│   ├── macros/                # Reusable Jinja macros (TBD)
│   ├── seeds/                 # CSV reference data (TBD: ytz_capacity)
│   ├── snapshots/             # SCD Type 2 (TBD: dim_airlines, dim_airports)
│   └── tests/                 # Custom singular data tests (TBD)
├── tests/                     # pytest unit tests for Python pipeline
├── docs/decisions/            # ADR: project design, dashboard structure, DAG
├── data/                      # Local NDJSON buffer (extract → load handoff)
├── setup_snowflake.sql        # DDL: database, schema, stage, table
├── requirements.txt           # Python dependencies
├── .env                       # Local credentials (git-ignored)
└── .github/workflows/         # CI/CD: tri-weekly extraction Mon/Wed/Fri 02:00 UTC
```

---

## Execution & Deployment

### Local Development
```bash
pip install -r requirements.txt
# WARNING: extract_flights.py uses live API quota — 2 requests per run
python src/extract_flights.py   # Fetch today's flights from API
python src/load_flights.py      # Load buffered files into Snowflake, archive on success
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
The `.github/workflows/daily_flight_extract.yml` workflow runs tri-weekly (Mon/Wed/Fri) at 02:00 UTC. Add your `.env` variables as GitHub Repository Secrets.
