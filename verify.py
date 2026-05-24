import sqlite3

conn = sqlite3.connect('predixion.db')
cursor = conn.cursor()

print('Tables in DB:')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cursor.fetchall())

print()
print('Rows in calls:', cursor.execute('SELECT COUNT(*) FROM calls').fetchone()[0])
print('Rows in ingestion_log:', cursor.execute('SELECT COUNT(*) FROM ingestion_log').fetchone()[0])

print()
print('Sample rows from calls:')
cursor.execute('SELECT call_id, agent_id, call_outcome, duration_bucket, call_hour FROM calls LIMIT 3')
for row in cursor.fetchall():
    print(row)

conn.close()