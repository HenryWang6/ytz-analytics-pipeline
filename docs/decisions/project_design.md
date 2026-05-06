# YTZ Analytics Dashboard Design

## Context
Portfolio project for an aviation enthusiast. Daily ELT pipeline ingests YTZ (Billy Bishop) flight data from AviationStack API into Snowflake, transforms with dbt, visualizes in Tableau.

**Key constraints:**
- AviationStack free tier: 100 req/month, 100 records/req. Extraction runs **3x/week (Mon/Wed/Fri)**, fetching both directions per run. At 2 requests/run × ~13 runs/month = ~26 req/month (74% headroom). The dbt incremental models (3-day and 7-day look-back windows) self-correct flight status transitions across runs — daily extracts are not necessary.
- `flight_date` parameter is **not available on free tier** (returns 403). The API returns flights from multiple dates sorted newest-first. Mitigation: client-side filter keeps only today's flights (`flight_date == today_str`). With `max_pages=1` (100 records), page 1 contains all of today's flights (74-78 on a typical day) plus some from yesterday — today's data is fully captured. On peak days (e.g., April 30: 101-104 records), 1-4 codeshare rows may fall to page 2 and be missed. All operating-carrier flights (~20-35/day) fit within 100. Acceptable trade-off for a portfolio project.
- The API is called **once per extract, never re-queried**. All dbt "look-back" logic operates on data already stored in Snowflake, not against the API.
- Data accumulates at ~13 complete snapshots/month — sufficient density for OTP and cancellation trend charts over weeks/months.

---

## Dashboard Structure: Two Sections

### Section 1 — Airport Overview (YTZ macro view)

All metrics at this level use **deduplicated (operating-carrier-only)** flight counts.

**KPIs across the top:**

| KPI | Definition |
|-----|-----------|
| Total Scheduled Flights | Total distinct physical flights scheduled (operating carrier only). Denominator for cancellation rate. |
| Total Actual Flights | Flights that actually operated (status != cancelled). Arrivals + departures, deduplicated. |
| Departure OTP % | % of completed departures within 15 min of scheduled time |
| Arrival OTP % | % of completed arrivals within 15 min of scheduled time |
| Cancellation Rate % | Cancelled flights / total scheduled flights |

**Charts:**
1. **Daily Flight Volume** — stacked bar (scheduled vs actual), x=date, y=count
2. **OTP Trend** — dual-line chart (departure OTP % + arrival OTP %), x=date, y=%
3. **Cancellation Trend** — combo chart: bar = cancelled count, line overlay = cancellation rate %
4. **Gate Workhorse Ranking** — horizontal bar, top N gates by flight count (operating carrier only)

---

### Section 2 — Airline Performance (drill-down by carrier)

**Airline dropdown filter** at top (single-select).

When a user selects an airline, they see ALL flights involving that airline — both flights it **operates** and flights it **markets** via codeshare. This gives a complete picture of that airline's presence at YTZ.

**KPIs across the top (filtered):**

| KPI | Definition |
|-----|-----------|
| Total Scheduled | All flights (operating + marketing) scheduled for this airline |
| Total Actual | All flights that actually operated |
| Departure OTP % | Airline-specific (all flights involving this airline) |
| Arrival OTP % | Airline-specific |
| Cancellation Rate % | Airline-specific |

**Charts:**
1. **Airline Daily Volume** — stacked bar (scheduled vs actual departures + arrivals), x=date
2. **Airline OTP Trend** — dual-line (departure OTP % + arrival OTP %), x=date
3. **Airline Cancellation Trend** — combo chart: bar = cancelled count, line = rate %, x=date
4. **Gate × Airline Affinity** — heatmap: rows=gate, cols=airline, cell=flight count. "Which gate should I go to for my Porter flight?"

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Codeshare handling | **Tag, don't drop.** Add `carrier_role` column (operating/marketing) + `operating_airline_iata`. Overview filters to operating only; airline view shows all rows for selected airline. | Physical flight count at overview; complete airline presence at drill-down. |
| OTP threshold | 15 minutes (industry standard) | Delay ≤15 min = on-time |
| OTP denominator | Completed flights only (actual time exists). Cancellations excluded. | A cancelled flight is not "late" — it never operated. Separate KPI tracks cancellations. |
| Cancellation detection | `LOWER(flight_status) IN ('cancelled', 'canceled')` | Handles both British and American API spellings |
| Time granularity | Daily snapshots | Simpler; hourly deferred to later phase |
| Runway utilization | Deferred | Needs hourly granularity + seed capacity data |
| Route analysis | Deferred | Revisit after core views are built |
| Gate analysis | Overview: workhorse ranking. Airline: gate affinity heatmap. | Avoids cluttering overview; airline affinity belongs at drill-down |
| Airline/Airport dims | **dbt snapshots (SCD2) from flight data**, not seeds | See rationale below |
| Summary grain | Group by BOTH scheduled_date and actual_operation_date | Flights near midnight can span two calendar dates; both perspectives matter |

### KPI Formulas

| KPI | Numerator | Denominator |
|-----|-----------|-------------|
| Departure OTP % | Departures with delay ≤ 15 min | Total completed departures (actual_dep IS NOT NULL) |
| Arrival OTP % | Arrivals with delay ≤ 15 min | Total completed arrivals (actual_arr IS NOT NULL) |
| Cancellation Rate % | Cancelled flights | Total scheduled flights |

### Why SCD2 snapshots instead of seeds for dims?

Airlines and airports look like static reference data at first glance, but:
- Airlines DO change: rebrands (Air Canada regional → Express), mergers, ICAO code updates
- Airports DO change: "Toronto City Centre Airport" → "Billy Bishop Toronto City Airport"
- Building dims from the source flight data means they're data-driven — a new airline appears in the data, it automatically flows into the dimension
- dbt snapshots are explicitly listed as a showcase item for this portfolio project
- If no changes occur during the project lifetime, the snapshot code still demonstrates the pattern correctly

**Seeds still have a role:** `ytz_capacity` (runway count, gate count, operating hours) — these are physical constants, making them genuinely good seed candidates.

---

## dbt Model DAG

```
source: RAW_DB.AVIATION.RAW_FLIGHTS (VARIANT)
  │  (populated by Python pipeline — NOT re-queried by dbt)
  │
  ├─ stg_raw_flights (view)
  │   Flatten JSON → typed columns. Preserve ALL rows (operating + marketing).
  │   Add derived columns:
  │     carrier_role:              'operating' if codeshared IS NULL, else 'marketing'
  │     operating_airline_iata:    airline.iata of the actual operator
  │     operating_flight_iata:     flight.iata of the actual operator
  │     flight_id:                 MD5(flight_date || operating_flight_iata || direction)
  │                                → same ID for all codeshare rows of the same physical flight
  │   Columns: flight_id, flight_date, direction, flight_status,
  │     dep_iata, arr_iata, airline_iata, airline_name,
  │     carrier_role, operating_airline_iata, operating_flight_iata,
  │     sched_dep, sched_arr, actual_dep, actual_arr,
  │     delay_dep, delay_arr, gate_dep, gate_arr,
  │     baggage, terminal_dep, terminal_arr, aircraft_icao24
  │   Test: enumerate distinct flight_status values to catch unexpected statuses early
  │
  ├─ dim_airlines (dbt snapshot → SCD2)
  │   FROM SELECT DISTINCT airline_iata, airline_name, airline_icao
  │   FROM stg_raw_flights. Natural key: airline_iata.
  │   dbt_valid_from / dbt_valid_to tracking.
  │
  ├─ dim_airports (dbt snapshot → SCD2)
  │   FROM SELECT DISTINCT airport_iata, airport_name, timezone
  │   FROM (departure airports UNION arrival airports) in stg_raw_flights.
  │   Natural key: airport_iata.
  │
  ├─ dim_dates (macro → table, full refresh)
  │   Standard date dimension via dbt_date or custom macro.
  │
  ├─ ytz_capacity (seed → table)
  │   Static reference: runway_count, gate_count, operating_hours_start,
  │   operating_hours_end.
  │
  ├─ int_flights_enriched (table, full refresh)
  │   stg_raw_flights JOIN dim_airlines, dim_airports (×2: dep + arr),
  │   dim_dates (×2: sched + actual). ALL rows preserved.
  │   Pre-computed: is_on_time_dep, is_on_time_arr, delay_bucket_dep,
  │     delay_bucket_arr, is_cancelled, actual_operation_date
  │     (COALESCE date(actual_dep), date(actual_arr))
  │   Central join point — all downstream models read from this, not stg directly.
  │
  ├─ fct_flights (incremental, merge on flight_id)
  │   Filter: carrier_role = 'operating'.
  │   One row per physical flight event.
  │   Merge updates: flight_status, actual_dep, actual_arr, delay_dep, delay_arr,
  │     is_on_time_dep, is_on_time_arr as flights transition scheduled→active→landed.
  │   Look-back window: 3 days (reads recent rows from Snowflake to catch status
  │     transitions — does NOT re-call the API).
  │   Tests: unique flight_id, not_null flight_id, valid flight_status values,
  │     delay between -60 and 1440 min.
  │
  ├─ daily_airport_summary (incremental, delete+insert on flight_date)
  │   FROM fct_flights. GROUP BY flight_date (scheduled date).
  │   Look-back: 7 days (rebuilds recent dates in Snowflake to self-correct
  │     when fct_flights merges updated statuses — no API involvement).
  │   Metrics: scheduled_dep, scheduled_arr, actual_dep, actual_arr,
  │     dep_otp_pct, arr_otp_pct, cancelled_count, cancellation_rate
  │
  ├─ daily_airport_operations (incremental, delete+insert on actual_operation_date)
  │   FROM fct_flights. GROUP BY actual_operation_date.
  │   Look-back: 7 days. Same metrics by calendar date of actual operation.
  │
  ├─ daily_airline_summary (incremental, delete+insert on (flight_date, airline_iata))
  │   FROM int_flights_enriched (ALL rows, operating + marketing).
  │   GROUP BY flight_date, airline_iata. Look-back: 7 days.
  │   NOTE: groups by airline_iata (not operating_airline_iata) so marketing-only
  │   carriers (Air Transat, United, Swiss) appear in the airline dropdown.
  │
  ├─ daily_airline_operations (incremental, delete+insert on (actual_operation_date, airline_iata))
  │   FROM int_flights_enriched. GROUP BY actual_operation_date, airline_iata.
  │   Look-back: 7 days.
  │
  └─ gate_usage_summary (table, full refresh)
      FROM int_flights_enriched (operating rows only).
      GROUP BY gate, airline_iata. flight_count.
      LEFT JOIN ytz_capacity for pct_gates_used (distinct gates / gate_count).
```

---

## Incremental Strategy

Flight data is **mutable over time**: a flight extracted on day T as `scheduled` becomes `active` on T+1 and `landed` with actual times on T+2. Static full-refresh builds would lose these transitions, leaving most flights permanently stuck at `scheduled`.

All look-back windows operate on **data already in Snowflake** (the `RAW_FLIGHTS` source and dbt models). They never trigger additional AviationStack API calls. The API is called only by the Python extraction pipeline, once per daily run.

| Model | Strategy | Rationale |
|-------|----------|-----------|
| `stg_raw_flights` | view | Always reflects current source, zero storage |
| `int_flights_enriched` | table (full refresh) | Cheap to rebuild (~200 rows/day). Re-evaluate at 10K+ rows |
| `fct_flights` | incremental, merge on `flight_id` | Flight status evolves. Merge upserts: new flights inserted, existing flights updated in place |
| `dim_airlines` | snapshot | dbt handles incrementality natively |
| `dim_airports` | snapshot | dbt handles incrementality natively |
| `dim_dates` | table (full refresh) | Generated once, rarely changes |
| `daily_airport_summary` | incremental, delete+insert | Rebuilds last 7 days in Snowflake to self-correct when fct_flights merges new statuses |
| `daily_airport_operations` | incremental, delete+insert | Same 7-day look-back |
| `daily_airline_summary` | incremental, delete+insert | Same 7-day look-back |
| `daily_airline_operations` | incremental, delete+insert | Same 7-day look-back |
| `gate_usage_summary` | table (full refresh) | Gate assignments don't change retroactively; small data |
| `ytz_capacity` | seed | Static physical constants |

### Why not simpler?

An alternative is full-refresh everything every run. With ~200 rows/day, Snowflake can handle that for months. Two reasons to use incremental instead:
1. **Portfolio demonstration** — incremental strategies (merge, delete+insert, snapshots) are a core analytics engineering skill worth showcasing.
2. **Correctness pattern** — even at small scale, the merge pattern shows how to handle mutable source data, which is a genuine requirement here (flight status transitions).

### Look-back windows

- **fct_flights: 3 days.** A flight scheduled Monday may not land (and get actual times) until Tuesday. A weekend flight's status might lag into Monday's extract.
- **Summary tables: 7 days.** Self-corrects aggregated metrics for dates where fct_flights rows were updated. 7 days is generous enough to cover weekend-lagged API updates.

All incremental models support `--full-refresh` for initial builds.

---

## Verification Plan
1. `dbt compile` — all models compile clean
2. `dbt test` — unique/not_null on fct_flights.flight_id, OTP % in 0-100% range
3. Spot-check: `COUNT(*)` in stg_raw_flights > `COUNT(*)` in fct_flights (marketing rows excluded from fact)
4. Same operating_flight_iata across codeshare rows → same flight_id in staging
5. Snapshot: dim_airlines has `dbt_valid_from`/`dbt_valid_to` columns, current rows have `dbt_valid_to IS NULL`
6. Seed: `ytz_capacity` feeds `gate_usage_summary.pct_gates_used`
7. Summary: `scheduled_dep` >= `actual_dep` in daily_airport_summary (cancellations explain the gap)
8. Airline dropdown: `SELECT DISTINCT airline_iata FROM daily_airline_summary` includes marketing-only carriers (TS, UA, LX)
9. Incremental: re-running `dbt run` on the same day produces idempotent results (no doubled counts)
10. flight_status coverage: dbt test on stg_raw_flights confirms expected statuses (scheduled, active, landed, cancelled/canceled) and flags any new ones
