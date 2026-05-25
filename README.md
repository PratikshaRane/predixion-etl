# Predixion AI — Data Engineering ETL Pipeline

An end-to-end ETL pipeline that ingests raw voice agent call logs,
validates and cleans them, loads them into SQLite, and answers
business questions through SQL queries.

---

## Project Structure
predixion_etl/
├── generate.py        # Task 1 — generates 500 raw noisy call records
├── pipeline.py        # Tasks 2, 3, 4 — ingestion, transformation, load
├── queries.py         # Task 5 — business analytics queries
├── test_pipeline.py   # Task 6 — unit tests (6 tests)
├── predixion.db       # SQLite database (generated after pipeline run)
├── outputs/           # CSV output files per business question
└── README.md
---

## Setup

**Requirements:** Python 3.10+

Install dependencies:
```bash
pip install pandas faker pytest
```

---

## How to Run (End to End)

**Step 1 — Generate raw data:**
```bash
python generate.py
```
Produces `raw_calls.json` with 525 records (500 base + noise injected).

**Step 2 — Run the pipeline:**
```bash
python pipeline.py
```
Validates, transforms, and loads 413 clean records into `predixion.db`.

**Step 3 — Run analytics queries:**
```bash
python queries.py
```
Answers 5 business questions. Results printed to terminal and saved in `outputs/`.

**Step 4 — Run unit tests:**
```bash
pytest test_pipeline.py -v
```
Runs 6 tests covering validation and transformation edge cases.

---

## Pipeline Summary

| Stage | Input | Output |
|-------|-------|--------|
| Generate | — | 525 raw records (raw_calls.json) |
| Ingest | 525 records | 413 accepted, 112 rejected |
| Transform | 413 records | Enriched with 6 new columns |
| Load | 413 records | Loaded into SQLite (idempotent) |

### Rejection Breakdown
| Reason | Count |
|--------|-------|
| missing_field | 82 |
| duplicate | 17 |
| bad_type | 13 |

---

## Business Questions Answered

| # | Question | Output File |
|---|----------|-------------|
| Q1 | Connect rate by language | q1_connect_rate_by_language.csv |
| Q2 | Hour with highest callback rate | q2_callback_rate_by_hour.csv |
| Q3 | Long call % and avg amount promised | q3_long_calls_analysis.csv |
| Q4 | Top 3 agents with outcome distribution | q4_top_agents.csv |
| Q5 | Call volume trend by date | q5_call_volume_by_date.csv |

---

## Design Choices

**Validation order matters:**
Records are checked for missing fields first, then duplicates, then bad types.
A record only gets one rejection reason — the first rule it fails.
This mirrors how real ingestion pipelines work.

**Idempotency:**
The `calls` table is cleared and reloaded on every run.
The `ingestion_log` table appends a new row each run for audit purposes.
This makes the pipeline safe to re-run without duplicating data.

**IST normalization:**
Raw timestamps are treated as UTC and converted to IST (Asia/Kolkata, UTC+5:30)
since Predixion operates in India. All derived columns (call_hour, call_date,
is_weekend) are based on IST.

**Amount imputation tracking:**
Null amount_promised values are filled with 0 but flagged with is_amount_imputed=True.
This preserves data lineage — downstream queries can exclude imputed values
when calculating averages (as done in Q3).

---

