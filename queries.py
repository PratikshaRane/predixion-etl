import sqlite3
import pandas as pd
import os

# ─────────────────────────────────────────
# TASK 5 — ANALYTICS / BUSINESS QUESTIONS
# ─────────────────────────────────────────

conn = sqlite3.connect("predixion.db")
os.makedirs("outputs", exist_ok=True)

def run_query(title, sql, filename):
    """Run a SQL query, print results, and save to CSV."""
    print("=" * 50)
    print(f"Q: {title}")
    print("=" * 50)
    df = pd.read_sql_query(sql, conn)
    print(df.to_string(index=False))
    df.to_csv(f"outputs/{filename}", index=False)
    print(f"Saved → outputs/{filename}")
    print()


# ── Q1: Connect rate by language ──
run_query(
    title="Connect rate by language",
    sql="""
        SELECT
            language,
            COUNT(*) AS total_calls,
            SUM(CASE WHEN call_outcome = 'connected' THEN 1 ELSE 0 END) AS connected_calls,
            ROUND(
                100.0 * SUM(CASE WHEN call_outcome = 'connected' THEN 1 ELSE 0 END) / COUNT(*),
                2
            ) AS connect_rate_pct
        FROM calls
        GROUP BY language
        ORDER BY connect_rate_pct DESC
    """,
    filename="q1_connect_rate_by_language.csv"
)


# ── Q2: Which hour has highest callback_requested rate ──
run_query(
    title="Hour with highest callback_requested rate",
    sql="""
        SELECT
            call_hour,
            COUNT(*) AS total_calls,
            SUM(CASE WHEN call_outcome = 'callback_requested' THEN 1 ELSE 0 END) AS callbacks,
            ROUND(
                100.0 * SUM(CASE WHEN call_outcome = 'callback_requested' THEN 1 ELSE 0 END) / COUNT(*),
                2
            ) AS callback_rate_pct
        FROM calls
        GROUP BY call_hour
        ORDER BY callback_rate_pct DESC
        LIMIT 5
    """,
    filename="q2_callback_rate_by_hour.csv"
)


# ── Q3: % of long calls and their average amount_promised ──
run_query(
    title="Long call % and average amount promised",
    sql="""
        SELECT
            duration_bucket,
            COUNT(*) AS total_calls,
            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM calls), 2) AS pct_of_total,
            ROUND(AVG(CASE WHEN is_amount_imputed = 0 THEN amount_promised END), 2) AS avg_amount_promised
        FROM calls
        GROUP BY duration_bucket
        ORDER BY total_calls DESC
    """,
    filename="q3_long_calls_analysis.csv"
)


# ── Q4: Top 3 agents by total calls with outcome distribution ──
run_query(
    title="Top 3 agents by total calls handled",
    sql="""
        SELECT
            agent_id,
            COUNT(*) AS total_calls,
            SUM(CASE WHEN call_outcome = 'connected'           THEN 1 ELSE 0 END) AS connected,
            SUM(CASE WHEN call_outcome = 'no_answer'           THEN 1 ELSE 0 END) AS no_answer,
            SUM(CASE WHEN call_outcome = 'dropped'             THEN 1 ELSE 0 END) AS dropped,
            SUM(CASE WHEN call_outcome = 'callback_requested'  THEN 1 ELSE 0 END) AS callback_requested
        FROM calls
        GROUP BY agent_id
        ORDER BY total_calls DESC
        LIMIT 3
    """,
    filename="q4_top_agents.csv"
)


# ── Q5: Call volume trend across dates ──
run_query(
    title="Call volume trend by date",
    sql="""
        SELECT
            call_date,
            COUNT(*) AS total_calls,
            SUM(CASE WHEN call_outcome = 'connected' THEN 1 ELSE 0 END) AS connected
        FROM calls
        GROUP BY call_date
        ORDER BY call_date ASC
    """,
    filename="q5_call_volume_by_date.csv"
)

conn.close()
print("All queries complete. Check the outputs/ folder!")