import pytest
import pandas as pd
from pipeline import validate_record, transform

# ─────────────────────────────────────────
# TASK 6 — UNIT TESTS
# ─────────────────────────────────────────

# A helper that builds a complete valid record
def make_record(overrides={}):
    record = {
        "call_id": "CALL_0001",
        "agent_id": "AGT_001",
        "customer_phone": "9876543210",
        "start_time": "2024-06-15T10:00:00",
        "end_time": "2024-06-15T10:05:00",
        "call_outcome": "connected",
        "language": "English",
        "disposition_code": "D01",
        "amount_promised": 5000.0,
        "retry_flag": True
    }
    record.update(overrides)
    return record


# ── Test 1: A valid record should pass validation ──
def test_valid_record_passes():
    record = make_record()
    is_valid, reason = validate_record(record, seen_ids=set())
    assert is_valid == True
    assert reason is None


# ── Test 2: A record with a missing required field should be rejected ──
def test_missing_field_rejected():
    record = make_record()
    del record["agent_id"]  # remove a required field
    is_valid, reason = validate_record(record, seen_ids=set())
    assert is_valid == False
    assert reason == "missing_field"


# ── Test 3: A duplicate call_id should be rejected ──
def test_duplicate_rejected():
    record = make_record()
    seen_ids = {"CALL_0001"}  # pretend we already saw this call_id
    is_valid, reason = validate_record(record, seen_ids=seen_ids)
    assert is_valid == False
    assert reason == "duplicate"


# ── Test 4: A malformed timestamp should be rejected ──
def test_bad_timestamp_rejected():
    record = make_record({"start_time": "NOT-A-DATE"})
    is_valid, reason = validate_record(record, seen_ids=set())
    assert is_valid == False
    assert reason == "bad_type"


# ── Test 5: Duration bucketing should work correctly ──
def test_duration_bucket():
    # We'll create 3 records with different durations and check buckets
    records = [
        make_record({"call_id": "CALL_0001", "start_time": "2024-06-15T10:00:00", "end_time": "2024-06-15T10:00:30"}),  # 30s → short
        make_record({"call_id": "CALL_0002", "start_time": "2024-06-15T10:00:00", "end_time": "2024-06-15T10:02:00"}),  # 120s → medium
        make_record({"call_id": "CALL_0003", "start_time": "2024-06-15T10:00:00", "end_time": "2024-06-15T10:10:00"}),  # 600s → long
    ]
    df = transform(records)
    buckets = df.set_index("call_id")["duration_bucket"].to_dict()

    assert buckets["CALL_0001"] == "short"
    assert buckets["CALL_0002"] == "medium"
    assert buckets["CALL_0003"] == "long"


# ── Test 6: Null amount_promised should be imputed with 0 and flagged ──
def test_amount_imputation():
    records = [
        make_record({"call_id": "CALL_0001", "amount_promised": None}),   # null → should be imputed
        make_record({"call_id": "CALL_0002", "amount_promised": 3000.0}), # has value → should NOT be imputed
    ]
    df = transform(records)
    df = df.set_index("call_id")

    # Null record should be 0 and flagged
    assert df.loc["CALL_0001", "amount_promised"] == 0
    assert df.loc["CALL_0001", "is_amount_imputed"] == True

    # Non-null record should be unchanged and not flagged
    assert df.loc["CALL_0002", "amount_promised"] == 3000.0
    assert df.loc["CALL_0002", "is_amount_imputed"] == False