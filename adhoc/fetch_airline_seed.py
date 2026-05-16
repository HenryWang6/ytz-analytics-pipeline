"""One-time utility: download openflights airlines.dat and write dbt seed CSV.

Cleans \\N (SQL null) and '-' (missing IATA) to empty strings so dbt
reads them as NULL in Snowflake.

Usage: python adhoc/fetch_airline_seed.py
Output: dbt/seeds/airline_mapping.csv
"""

import csv
import os
import sys
import urllib.request

URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
COLUMNS = ["airline_id", "airline_name", "alias", "iata", "icao", "callsign", "country", "active"]

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(PROJECT_ROOT, "dbt", "seeds", "airline_mapping.csv")


def clean(field_index: int, value: str) -> str:
    """Clean individual field values for dbt compatibility."""
    stripped = value.strip()
    # Replace SQL null and missing-IATA sentinels
    if stripped in ("\\N", "-"):
        return ""
    # Normalize active flag to uppercase
    if field_index == 7 and stripped.lower() in ("y", "n"):
        return stripped.upper()
    return value


def main():
    print(f"Downloading {URL} ...")
    with urllib.request.urlopen(URL) as response:
        raw = response.read().decode("utf-8")

    reader = csv.reader(raw.splitlines())
    rows_written = 0

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)

        for row in reader:
            if len(row) != 8:
                print(f"  Skipping malformed row (expected 8 cols, got {len(row)}): {row[:3]}...")
                continue
            cleaned = [clean(i, field) for i, field in enumerate(row)]
            writer.writerow(cleaned)
            rows_written += 1

    print(f"Wrote {rows_written} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
