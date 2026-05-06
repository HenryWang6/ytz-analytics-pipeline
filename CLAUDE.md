# YTZ Analytics Pipeline
> A production-grade aviation data pipeline — API extraction to dbt-modeled analytics in Snowflake — built to demonstrate end-to-end analytics engineering with testing, documentation, and CI/CD.

## Tech Stack
- Python 3.11.7 (pyenv virtualenv `portfolio_dbt_env`)
- Snowflake (free trial)
- dbt Core 1.11.8 + dbt-snowflake 1.11.4
- GitHub Actions (tri-weekly orchestration, Mon/Wed/Fri 02:00 UTC)
- Tableau (dashboards built externally)
- Key dependencies: snowflake-connector-python, requests, python-dotenv, dbt-core, dbt-snowflake, dbt-utils, dbt-expectations
- Build: none — scripts run directly via `python`

## Conventions
- Code style: clean, readable, no strict formatter/linter enforced
- dbt structure: staging → marts (intermediate layer added only if complexity demands it), following dbt Labs recommended best practices
- Python: OOP classes with `main()` entry points, logger per module, centralized config
- Testing: pytest for Python pipeline code, dbt schema tests (unique, not_null) + dbt-expectations for data quality
- Commit style: `<type>: <short description>` — body explains *why*, not *what*

## Key Paths
- `src/` — Python pipeline code (API extraction, Snowflake loader, centralized config)
- `dbt/` — dbt project (models/staging, models/marts, macros, seeds, snapshots, tests)
- `tests/` — pytest unit tests for Python pipeline

## Scope
- Daily batch ELT pipeline for Toronto Island Airport (YTZ)
- Raw JSON ingestion into Snowflake VARIANT column (schema-on-read)
- dbt staging and marts models with testing and documentation
- pytest unit tests + dbt data quality tests
- CI/CD via GitHub Actions

Out of scope: historical backfill, multi-airport support, real-time/streaming, Tableau dashboards (built externally)
<!-- When scope changes: update this list. Save the *reason* to project memory (if only Claude needs it) or docs/decisions/ (if the team needs it too). -->

## Active Decisions
- All major design decisions settled and documented in `docs/decisions/project_design.md` (dashboard structure, codeshare handling, SCD2 dims, incremental dbt strategy, KPI formulas).
- Rate limit strategy **implemented**: extraction 3x/week (Mon/Wed/Fri), client-side date filter (`flight_date == today`), `max_pages=1` pagination cap, file-level dedup via `data/archive/`. ~26 req/month (74% headroom under 100 limit). Note: `flight_date` API param blocked on free tier (403), so filtering is client-side only.
- Next: implement dbt staging models (`stg_raw_flights.sql`), dims, and fact table per the design doc DAG.
<!-- For settled architecture decisions with full rationale, write them up in docs/decisions/ (version-controlled, team-visible). -->

## Constraints
- AviationStack free tier: 100 requests/month, 100 records/request. Extraction runs 3x/week (Mon/Wed/Fri). Never run extract_flights.py for testing — use cached data files or mocked API responses
- Snowflake free trial — confirm account is active before running load or dbt operations
- Loaded NDJSON files move to `data/archive/` — prevents re-loading duplicates into Snowflake

---

## Claude Code Workflow (shared across all projects)

### Decision triggers

| When | Then |
|------|------|
| New feature, >2 files, or architectural choice | **Plan Mode** — design first, code after approval |
| 3+ distinct steps | **TaskCreate** — track each step, use dependencies |
| Need to search/explore codebase | **Explore Agent** (don't guess file paths) |
| Multi-step research spanning many files | **general-purpose Agent** |
| Implementation done | **Review** — check edge cases, security, over-engineering |
| Scope or priorities changed | **Update CLAUDE.md** `## Scope` / `## Active Decisions` — keep it lightweight (2-3 lines) |
| Settled an architecture decision | **Write an ADR** in `docs/decisions/` with full rationale — litmus test: would another dev need this? |
| User corrects approach or gives feedback | **Save to Memory** immediately |
| User says "remember X" | **Save to Memory** immediately |

### Anti-patterns to avoid
- Don't Plan Mode for trivial fixes (typo, single-line change)
- Don't mock in tests unless the user explicitly approves it
- Don't over-engineer — three similar lines > premature abstraction
- Don't add error handling for scenarios that can't happen
- Don't create docs/README unless asked (docs/decisions/ ADRs are the exception — create those when architecture decisions settle)

### Commit style
- `<type>: <short description>` — type is feat/fix/chore/docs/refactor/test
- Body explains *why*, not *what*
- Append `Co-Authored-By: Claude Code <noreply@anthropic.com>`
