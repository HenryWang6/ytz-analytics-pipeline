# Aviation Data Pipeline: Toronto Island Airport (YTZ)

## Project Overview
This project is an automated, production-grade ELT (Extract, Load, Transform) data pipeline designed to pull live, daily flight data from the AviationStack API and ingest it into a Snowflake data warehouse. 

The pipeline specifically targets all arriving and departing flights for Toronto Island Airport (YTZ), taking advantage of the airport's low daily volume to capture a comprehensive, daily snapshot without exceeding API limits.

---

## 🏗️ Architecture & Design Choices

The project was built adhering to modern software engineering and data engineering best practices:

### 1. Separation of Concerns (Decoupled ELT)
Instead of a single monolithic script, the extraction and loading phases are strictly separated:
*   **Extract Phase (`extract_flights.py`)**: Fetches data from the API, handles pagination, and buffers the raw JSON payload to a local `./data/` directory.
*   **Load Phase (`load_flights.py`)**: Scans the `./data/` directory, connects to Snowflake, and loads any pending files. 
*   *Why?* If the Snowflake connection fails, the API quota isn't wasted. The JSON file remains safely stored locally, ready to be picked up during the next load attempt.

### 2. Object-Oriented Programming (OOP)
The core logic is wrapped in classes (`AviationAPIClient` and `SnowflakeLoader`). The entry points (`main()`) merely orchestrate the logic by passing in configurations. This makes the code highly modular and unit-testable.

### 3. Centralized Configuration (`config.py`)
All environment variables, directory paths, and default limits are loaded in a single `config.py` file. This acts as the Single Source of Truth for the entire application, validating credentials before any expensive operations occur.

### 4. Snowflake Internal Staging
Rather than attempting row-by-row inserts, the loading script utilizes Snowflake's internal stages. It executes a `PUT` command to securely upload the local JSON files to the cloud, followed by a `COPY INTO` command for lightning-fast bulk ingestion.

### 5. Flexible Schema-on-Read (`VARIANT`)
The target Snowflake table (`RAW_DB.AVIATION.RAW_FLIGHTS`) uses a `VARIANT` column to store the raw nested JSON. This embraces the modern ELT philosophy: load everything raw first, then handle schema parsing and transformations downstream using dbt or SQL views.

---

## 📂 File Structure

```text
aviation_portfolio_project/
├── config.py                 # Centralized config, env loading, & logger setup
├── extract_flights.py        # AviationAPIClient and extraction orchestration
├── load_flights.py           # SnowflakeLoader and file ingestion orchestration
├── setup_snowflake.sql       # DDL commands to create DB, Schema, Stage, and Table
├── .env                      # Local credentials (ignored in git)
├── .github/
│   └── workflows/
│       └── daily_flight_extract.yml  # CI/CD orchestration for daily runs
└── data/                     # Temporary local buffer for NDJSON files
```

---

## 🚀 Execution & Deployment

### Local Development
To run the pipeline locally, ensure your `.env` file is populated with valid AviationStack and Snowflake credentials, then run:
```bash
python extract_flights.py
python load_flights.py
```

### Production Orchestration (GitHub Actions)
This pipeline is fully automated via GitHub Actions.
1. Add your `.env` variables as **Repository Secrets** in your GitHub repository.
2. The included `.github/workflows/daily_flight_extract.yml` will automatically spin up an Ubuntu container, install dependencies, and execute the scripts sequentially every day at **02:00 UTC**.
