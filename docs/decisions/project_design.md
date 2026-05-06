# YTZ Analytics Dashboard Design

## Context
Portfolio project for an aviation enthusiast. Daily ELT pipeline ingests YTZ (Billy Bishop) flight data from AviationStack API into Snowflake, transforms with dbt, visualizes in Tableau.

**Key constraints:**
- AviationStack free tier: 50 req/month, 100 records/req. With codeshare inflation, a single day at YTZ may return more than 100 records (each physical flight appears 2-3x across operating + marketing carriers). **Risk to investigate:** does the free tier paginate reliably past 100, or will we lose records? Mitigation options: split by AM/PM windows, accept partial data, or test empirically.
- Data accumulates slowly — one extract per day builds history over weeks/months.

---

## Dashboard Structure: Two Sections

### Section 1 — Airport Overview (YTZ macro view)

All metrics at this level use **deduplicated (operating-carrier-only)** flight counts.

**KPIs across the top:**

| KPI | Definition |
|-----|-----------|
| Total Scheduled Flights | Total distinct physical flights scheduled (operating carrier only). Denominator for OTP and cancellation rate. |
| Total Actual Flights | Flights that actually operated (status != cancelled). Arrivals + departures, deduplicated. |
| Departure OTP % | % of departures departing within 15 min of scheduled time |
| Arrival OTP % | % of arrivals arriving within 15 min of scheduled time |
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
| Total Actual | Flights that actually operated |
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
| Time granularity | Daily snapshots | Simpler; hourly deferred to later phase |
| Runway utilization | Deferred | Needs hourly granularity + seed capacity data |
| Route analysis | Deferred | Revisit after core views are built |
| Cancellation definition | `flight_status = 'cancelled'` | Direct from API |
| Gate analysis | Overview: workhorse ranking. Airline: gate affinity heatmap. | Avoids cluttering overview; airline affinity belongs at drill-down |
| Airline/Airport dims | **dbt snapshots (SCD2) from flight data**, not seeds | Airlines can rebrand/merge; airports can rename. dbt snapshots demonstrate a key portfolio skill. Seeds used only for truly static data (ytz_capacity). |
| Summary grain | Group by BOTH scheduled_date and actual_operation_date | Flights near midnight can span two calendar dates; both perspectives matter |

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
  │
  ├─ stg_raw_flights (view)
  │   Flatten JSON → typed columns. Preserve ALL rows (operating + marketing).
  │   Add derived columns:
  │     carrier_role:              'operating' if codeshared IS NULL, else 'marketing'
  │     operating_airline_iata:    airline.iata of the actual operator
  │     operating_flight_iata:     flight.iata of the actual operator
  │     flight_id:                 MD5(flight_date || operating_flight_iata || direction)
  │                                → same ID for all codeshare rows of the same physical flight
  │
  ├─ dim_airlines (dbt snapshot → SCD2)
  │   Snapshot from SELECT DISTINCT airline_iata, airline_name, airline_icao
  │   FROM stg_raw_flights. Natural key: airline_iata.
  │
  ├─ dim_airports (dbt snapshot → SCD2)
  │   Snapshot from SELECT DISTINCT airport_iata, airport_name, timezone
  │   FROM (departure airports UNION arrival airports) in stg_raw_flights.
  │   Natural key: airport_iata.
  │
  ├─ dim_dates (macro → table)
  │   Standard date dimension via dbt_date or custom macro.
  │
  ├─ ytz_capacity (seed → table)
  │   Static reference: runway_count, gate_count, operating_hours_start,
  │   operating_hours_end.
  │
  ├─ fct_flights (table)
  │   One row per physical flight event (carrier_role = 'operating').
  │   Joins: dim_airlines, dim_airports (×2: dep + arr), dim_dates (×2: sched + actual).
  │   Derived: is_on_time_dep, is_on_time_arr, delay_bucket_dep, delay_bucket_arr,
  │     is_cancelled, actual_operation_date (COALESCE date(actual_dep), date(actual_arr))
  │   Tests: unique flight_id, not_null flight_id, valid flight_status,
  │     delay between -60 and 1440 min
  │
  ├─ daily_airport_summary (table)
  │   GROUP BY flight_date (scheduled date). Airport-level KPIs.
  │
  ├─ daily_airport_operations (table)
  │   GROUP BY actual_operation_date. Airport-level KPIs by calendar date
  │   of actual operation.
  │
  ├─ daily_airline_summary (table)
  │   GROUP BY flight_date, operating_airline_iata. Airline KPIs by scheduled date.
  │
  ├─ daily_airline_operations (table)
  │   GROUP BY actual_operation_date, operating_airline_iata. Airline KPIs
  │   by actual operation date.
  │
  └─ gate_usage_summary (table)
      GROUP BY gate, operating_airline_iata. flight_count.
      Identifies workhorse gates and airline-gate affinity.
```

---

## Verification Plan
1. `dbt compile` — all models compile clean
2. `dbt test` — unique/not_null on fct_flights.flight_id, OTP % in 0-100 range
3. Spot-check: `COUNT(*)` in stg_raw_flights > `COUNT(*)` in fct_flights (marketing rows excluded from fact)
4. Same operating_flight_iata across codeshare rows → same flight_id in staging
5. Snapshot: dim_airlines has `dbt_valid_from`/`dbt_valid_to` columns, current rows have `dbt_valid_to IS NULL`
6. Seed: `ytz_capacity` referential integrity
7. Summary: `scheduled_dep` >= `actual_dep` in daily_airport_summary (cancellations explain the gap)
