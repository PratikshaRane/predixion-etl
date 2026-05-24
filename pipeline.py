import json
import pandas as pd
from datetime import datetime

# ─────────────────────────────────────────
# TASK 2 — INGESTION & VALIDATION
# ─────────────────────────────────────────

REQUIRED_FIELDS = [
    "call_id", "agent_id", "customer_phone", "start_time",
    "end_time", "call_outcome", "language", "disposition_code", "retry_flag"
]

VALID_OUTCOMES = {"connected", "no_answer", "dropped", "callback_requested"}
VALID_LANGUAGES = {"Hindi", "English", "Marathi"}

def validate_record(record, seen_ids):
    """
    Validate a single record.
    Returns (is_valid, reason)
    """

    # Check 1 — missing required fields
    for field in REQUIRED_FIELDS:
        if field not in record or record[field] is None:
            return False, "missing_field"

    # Check 2 — duplicate call_id
    if record["call_id"] in seen_ids:
        return False, "duplicate"

    # Check 3 — bad timestamp format
    for ts_field in ["start_time", "end_time"]:
        try:
            datetime.strptime(record[ts_field], "%Y-%m-%dT%H:%M:%S")
        except (ValueError, TypeError):
            return False, "bad_type"

    # Check 4 — invalid categorical values
    if record["call_outcome"] not in VALID_OUTCOMES:
        return False, "bad_type"
    if record["language"] not in VALID_LANGUAGES:
        return False, "bad_type"

    return True, None


def ingest(filepath="raw_calls.json"):
    """
    Read raw JSON, validate each record.
    Returns clean_records (list) and rejected_log (list).
    """

    with open(filepath, "r") as f:
        raw_data = json.load(f)

    clean_records = []
    rejected_log = []
    seen_ids = set()  # track call_ids we've already accepted

    for record in raw_data:
        is_valid, reason = validate_record(record, seen_ids)

        if is_valid:
            seen_ids.add(record["call_id"])
            clean_records.append(record)
        else:
            rejected_log.append({
                "call_id": record.get("call_id", "UNKNOWN"),
                "reason": reason
            })

    return clean_records, rejected_log
# ─────────────────────────────────────────
# TASK 3 — TRANSFORMATION
# ─────────────────────────────────────────

def transform(clean_records):
    """
    Takes clean records list, returns enriched DataFrame.
    """
    df = pd.DataFrame(clean_records)

    # Step 1 — Deduplicate: keep latest record per call_id by start_time
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])
    df = df.sort_values("start_time", ascending=False)
    df = df.drop_duplicates(subset="call_id", keep="first")

    # Step 2 — Normalize to IST (UTC+5:30)
    # Our generated times have no timezone, we treat them as UTC and convert
    df["start_time_ist"] = df["start_time"].dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
    df["end_time_ist"]   = df["end_time"].dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")

    # Step 3 — Compute call duration in seconds
    df["call_duration_seconds"] = (df["end_time_ist"] - df["start_time_ist"]).dt.total_seconds().astype(int)

    # Step 4 — Derive call_hour, call_date, is_weekend
    df["call_hour"]  = df["start_time_ist"].dt.hour
    df["call_date"]  = df["start_time_ist"].dt.date
    df["is_weekend"] = df["start_time_ist"].dt.dayofweek >= 5  # 5=Saturday, 6=Sunday

    # Step 5 — Bucket duration
    def bucket_duration(seconds):
        if seconds < 60:
            return "short"
        elif seconds <= 300:
            return "medium"
        else:
            return "long"

    df["duration_bucket"] = df["call_duration_seconds"].apply(bucket_duration)

    # Step 6 — Impute amount_promised nulls
    df["is_amount_imputed"] = df["amount_promised"].isna()
    df["amount_promised"]   = df["amount_promised"].fillna(0)

    return df
# ─────────────────────────────────────────
# TASK 4 — LOAD INTO SQLITE
# ─────────────────────────────────────────

import sqlite3
from datetime import datetime, timezone

def load(transformed_df, rejected_count, db_path="predixion.db"):
    """
    Persist transformed records and run metadata to SQLite.
    Idempotent — safe to re-run without duplicating data.
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ── Create calls table if it doesn't exist ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            call_id               TEXT PRIMARY KEY,
            agent_id              TEXT,
            customer_phone        TEXT,
            start_time_ist        TEXT,
            end_time_ist          TEXT,
            call_outcome          TEXT,
            language              TEXT,
            disposition_code      TEXT,
            amount_promised       REAL,
            retry_flag            INTEGER,
            call_duration_seconds INTEGER,
            call_hour             INTEGER,
            call_date             TEXT,
            is_weekend            INTEGER,
            duration_bucket       TEXT,
            is_amount_imputed     INTEGER
        )
    """)

    # ── Create ingestion_log table if it doesn't exist ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_log (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            run_timestamp     TEXT,
            records_processed INTEGER,
            records_rejected  INTEGER,
            records_loaded    INTEGER
        )
    """)

    # ── Idempotency: clear calls table before reloading ──
    cursor.execute("DELETE FROM calls")

    # ── Prepare DataFrame for SQLite ──
    df_to_load = transformed_df.copy()

    # Convert timestamps to strings (SQLite doesn't have a datetime type)
    df_to_load["start_time_ist"] = df_to_load["start_time_ist"].astype(str)
    df_to_load["end_time_ist"]   = df_to_load["end_time_ist"].astype(str)
    df_to_load["call_date"]      = df_to_load["call_date"].astype(str)

    # Convert booleans to integers (SQLite stores booleans as 0/1)
    df_to_load["is_weekend"]        = df_to_load["is_weekend"].astype(int)
    df_to_load["is_amount_imputed"] = df_to_load["is_amount_imputed"].astype(int)
    df_to_load["retry_flag"]        = df_to_load["retry_flag"].astype(int)

    # Keep only the columns our table expects
    columns = [
        "call_id", "agent_id", "customer_phone", "start_time_ist",
        "end_time_ist", "call_outcome", "language", "disposition_code",
        "amount_promised", "retry_flag", "call_duration_seconds",
        "call_hour", "call_date", "is_weekend", "duration_bucket",
        "is_amount_imputed"
    ]
    df_to_load = df_to_load[columns]

    # ── Load records into calls table ──
    df_to_load.to_sql("calls", conn, if_exists="append", index=False)

    # ── Log this pipeline run ──
    cursor.execute("""
        INSERT INTO ingestion_log (run_timestamp, records_processed, records_rejected, records_loaded)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        525,
        rejected_count,
        len(df_to_load)
    ))

    conn.commit()
    conn.close()

    print(f"Loaded {len(df_to_load)} records into '{db_path}'")
    print(f"Run logged in ingestion_log table.")
# ─────────────────────────────────────────
# RUN & PRINT SUMMARY
# ─────────────────────────────────────────

if __name__ == "__main__":
    clean, rejected = ingest()

    clean_df = pd.DataFrame(clean)
    rejected_df = pd.DataFrame(rejected)

    print("=" * 40)
    print("INGESTION SUMMARY")
    print("=" * 40)
    print(f"Total records read  : 525")
    print(f"Total accepted      : {len(clean_df)}")
    print(f"Total rejected      : {len(rejected_df)}")
    print()
    print("Rejection breakdown:")
    print(rejected_df["reason"].value_counts().to_string())
    print("=" * 40)

    # Task 3
    transformed_df = transform(clean)

    print()
    print("=" * 40)
    print("TRANSFORMATION SUMMARY")
    print("=" * 40)
    print(f"Records after dedup     : {len(transformed_df)}")
    print(f"Amount nulls imputed    : {transformed_df['is_amount_imputed'].sum()}")
    print()
    print("Duration bucket breakdown:")
    print(transformed_df["duration_bucket"].value_counts().to_string())
    print("=" * 40)

    # Task 4
    print()
    print("=" * 40)
    print("LOAD SUMMARY")
    print("=" * 40)
    load(transformed_df, rejected_count=len(rejected_df))
    print("=" * 40)