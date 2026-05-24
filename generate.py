import json
import random
from datetime import datetime, timedelta

# Fixed seed = same data every time you run it (reproducible)
random.seed(42)

# --- Constants ---
AGENT_IDS = [f"AGT_{i:03d}" for i in range(1, 21)]          # AGT_001 to AGT_020
OUTCOMES = ["connected", "no_answer", "dropped", "callback_requested"]
LANGUAGES = ["Hindi", "English", "Marathi"]
DISPOSITION_CODES = ["D01", "D02", "D03", "D04", "D05"]

def random_phone():
    """Generate a fake 10-digit Indian mobile number."""
    return f"9{random.randint(100000000, 999999999)}"

def random_timestamp(start_date, end_date):
    """Return a random datetime string between two dates."""
    delta = end_date - start_date
    random_seconds = random.randint(0, int(delta.total_seconds()))
    dt = start_date + timedelta(seconds=random_seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")

def generate_record(call_id):
    """Generate one clean call record."""
    start = datetime(2024, 6, 1)
    end = datetime(2024, 6, 30)

    start_time = random_timestamp(start, end)
    # end_time is start_time + 30s to 600s (call duration)
    start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
    end_dt = start_dt + timedelta(seconds=random.randint(30, 600))

    return {
        "call_id": f"CALL_{call_id:04d}",
        "agent_id": random.choice(AGENT_IDS),
        "customer_phone": random_phone(),
        "start_time": start_time,
        "end_time": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "call_outcome": random.choice(OUTCOMES),
        "language": random.choice(LANGUAGES),
        "disposition_code": random.choice(DISPOSITION_CODES),
        "amount_promised": round(random.uniform(500, 50000), 2) if random.random() > 0.3 else None,
        "retry_flag": random.choice([True, False])
    }

# --- Generate 500 base records ---
records = [generate_record(i) for i in range(1, 501)]

# --- Inject ~5% duplicates (25 records) ---
duplicates = random.sample(records, 25)
records.extend(duplicates)

# --- Inject ~15% missing fields (75 records) ---
fields_to_drop = ["agent_id", "call_outcome", "language", "disposition_code", "retry_flag"]
missing_indices = random.sample(range(len(records)), 75)
for idx in missing_indices:
    field = random.choice(fields_to_drop)
    records[idx].pop(field, None)

# --- Inject ~3% malformed timestamps (15 records) ---
bad_ts_indices = random.sample(range(len(records)), 15)
for idx in bad_ts_indices:
    records[idx]["start_time"] = "NOT-A-DATE"

# --- Shuffle so noise is spread throughout ---
random.shuffle(records)

# --- Save to JSON ---
with open("raw_calls.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"Generated {len(records)} records → raw_calls.json")
print(f"  Base records : 500")
print(f"  Duplicates   : 25")
print(f"  Missing fields: ~75")
print(f"  Bad timestamps: ~15")