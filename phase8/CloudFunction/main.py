import functions_framework
import pandas as pd
import numpy as np
import os
import io
from sqlalchemy import create_engine, text
from google.cloud import storage

# ── Config ────────────────────────────────────────────────────────────────────
DATABASE_URL = (
    f"postgresql://{os.environ.get('DB_USER', 'admin')}:"
    f"{os.environ.get('DB_PASSWORD')}@"
    f"{os.environ.get('DB_HOST')}:"
    f"{os.environ.get('DB_PORT', '5432')}/"
    f"{os.environ.get('DB_NAME', 'trip_db')}"
)

MILES_TO_KM     = 1.60934
REFERENCE_SPEED = 12.0
SLOW_KMH        = 15.0
FAST_KMH        = 30.0
PAYMENT_MAP     = {1: "card", 2: "cash", 3: "no_charge", 4: "dispute"}
CHUNK_SIZE      = 50000  # Process 50k rows at a time to avoid memory issues
MAX_ROWS        = 10000
# ── Helpers ───────────────────────────────────────────────────────────────────

def classify_time(hour):
    if 7 <= hour <= 9 or 16 <= hour <= 19:
        return "peak"
    elif hour >= 22 or hour < 6:
        return "night"
    return "off_peak"


def compute_deviation(distance_mi, duration_min):
    if distance_mi <= 0 or duration_min <= 0:
        return None, None
    expected = (distance_mi / REFERENCE_SPEED) * 60
    rdi = duration_min / expected
    if rdi <= 1.20:
        cls = "efficient"
    elif rdi <= 1.60:
        cls = "moderate"
    else:
        cls = "inefficient"
    return round(rdi, 4), cls


def compute_speed(distance_mi, duration_min):
    if distance_mi <= 0 or duration_min <= 0:
        return None, None
    speed = (distance_mi * MILES_TO_KM) / (duration_min / 60.0)
    if speed >= 200:
        return None, None
    if speed < SLOW_KMH:
        cls = "slow"
    elif speed <= FAST_KMH:
        cls = "normal"
    else:
        cls = "fast"
    return round(speed, 2), cls


def compute_suspicion(row):
    score = 0
    dist  = row["trip_distance"]
    dur   = row["trip_duration_min"]
    fare  = row["fare_amount"]
    tip   = row["tip_amount"]
    pax   = row["passenger_count"]
    if pd.notna(dist) and pd.notna(fare):
        if dist > 0 and dist < 2 and fare > 30:
            score += 1
        if dist == 0 and fare > 5:
            score += 1
    if pd.notna(fare) and fare < 0:
        score += 1
    if pd.notna(dist) and pd.notna(dur) and dur > 0:
        if dist / (dur / 60.0) > 100:
            score += 1
    if pd.notna(dur) and pd.notna(dist) and dur == 0 and dist > 0:
        score += 1
    if pd.notna(tip) and pd.notna(fare) and fare > 0 and tip > fare * 2:
        score += 1
    if pd.notna(fare) and fare > 200:
        score += 1
    if pd.notna(pax) and pax <= 0:
        score += 1
    return score


def process_chunk(chunk):
    """Process a single chunk of the CSV."""
    chunk["tpep_pickup_datetime"]  = pd.to_datetime(chunk["tpep_pickup_datetime"])
    chunk["tpep_dropoff_datetime"] = pd.to_datetime(chunk["tpep_dropoff_datetime"])
    chunk["trip_duration_min"]     = (
        chunk["tpep_dropoff_datetime"] - chunk["tpep_pickup_datetime"]
    ).dt.total_seconds() / 60.0

    for col in ["pickup_zone_id", "dropoff_zone_id", "trip_distance",
                "fare_amount", "tip_amount", "passenger_count", "payment_type"]:
        chunk[col] = pd.to_numeric(chunk[col], errors="coerce")

    chunk = chunk.dropna(subset=[
        "tpep_pickup_datetime", "tpep_dropoff_datetime",
        "pickup_zone_id", "dropoff_zone_id",
        "trip_distance", "fare_amount"
    ])

    chunk["time_class"]       = chunk["tpep_pickup_datetime"].dt.hour.apply(classify_time)
    chunk["trip_distance_km"] = chunk["trip_distance"] * MILES_TO_KM

    deviation = chunk.apply(lambda r: compute_deviation(r["trip_distance"], r["trip_duration_min"]), axis=1)
    chunk["deviation_index"] = deviation.apply(lambda x: x[0])
    chunk["deviation_class"] = deviation.apply(lambda x: x[1])

    speed = chunk.apply(lambda r: compute_speed(r["trip_distance"], r["trip_duration_min"]), axis=1)
    chunk["avg_speed_kmh"] = speed.apply(lambda x: x[0])
    chunk["speed_class"]   = speed.apply(lambda x: x[1])

    chunk["suspicion_score"]  = chunk.apply(compute_suspicion, axis=1)
    chunk["payment_type_str"] = chunk["payment_type"].map(PAYMENT_MAP).fillna("unknown")

    chunk = chunk.where(pd.notnull(chunk), other=None)
    chunk["avg_speed_kmh"]   = chunk["avg_speed_kmh"].astype(object).where(chunk["avg_speed_kmh"].notna(), None)
    chunk["deviation_index"] = chunk["deviation_index"].astype(object).where(chunk["deviation_index"].notna(), None)

    return chunk[[
        "tpep_pickup_datetime", "tpep_dropoff_datetime",
        "pickup_zone_id", "dropoff_zone_id",
        "pickup_zone_name", "dropoff_zone_name",
        "trip_distance_km", "fare_amount", "tip_amount",
        "passenger_count", "payment_type_str",
        "time_class", "deviation_index", "deviation_class",
        "avg_speed_kmh", "speed_class", "suspicion_score",
    ]].rename(columns={
        "tpep_pickup_datetime":  "pickup_datetime",
        "tpep_dropoff_datetime": "dropoff_datetime",
        "payment_type_str":      "payment_type",
    })

# ── Main Function ─────────────────────────────────────────────────────────────

@functions_framework.cloud_event
def ingest_trips(cloud_event):
    """Triggered by a file upload to a GCS bucket."""

    data        = cloud_event.data
    bucket_name = data["bucket"]
    file_name   = data["name"]

    print(f"Triggered by file: {file_name} in bucket: {bucket_name}")

    if not file_name.endswith(".csv"):
        print(f"Skipping non-CSV file: {file_name}")
        return

    # ── Download CSV from GCS ─────────────────────────────────────────────────
    print("Downloading CSV from GCS...")
    client  = storage.Client()
    bucket  = client.bucket(bucket_name)
    blob    = bucket.blob(file_name)
    content = blob.download_as_bytes()
    print("Download complete")

    # ── Connect to DB ─────────────────────────────────────────────────────────
    print("Connecting to database...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE trips RESTART IDENTITY CASCADE;"))
            conn.commit()
        print("Connected and truncated table")
    except Exception as e:
        print(f"ERROR: Failed to connect to DB — {e}")
        raise

    # ── Process CSV in chunks ─────────────────────────────────────────────────
    print(f"Processing CSV in chunks of {CHUNK_SIZE} rows (max {MAX_ROWS} rows)...")
    total_inserted = 0

    for chunk in pd.read_csv(
        io.BytesIO(content),
        usecols=[
            "tpep_pickup_datetime", "tpep_dropoff_datetime",
            "passenger_count", "trip_distance",
            "pickup_zone_id", "pickup_zone_name",
            "dropoff_zone_id", "dropoff_zone_name",
            "fare_amount", "tip_amount", "total_amount", "payment_type",
        ],
        chunksize=CHUNK_SIZE,
        nrows=MAX_ROWS,
    ):
        remaining = MAX_ROWS - total_inserted
        chunk = chunk.head(remaining)

        df_insert = process_chunk(chunk)
        df_insert.to_sql("trips", engine, if_exists="append", index=False)
        total_inserted += len(df_insert)
        print(f"Inserted {total_inserted} rows so far...")

        if total_inserted >= MAX_ROWS:
            print(f"Reached MAX_ROWS limit ({MAX_ROWS}). Stopping.")
            break

    print(f"SUCCESS: {total_inserted} trips inserted from file {file_name}")
