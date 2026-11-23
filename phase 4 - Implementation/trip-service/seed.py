import psycopg2
import pandas as pd
import numpy as np
import sys
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# ── Config ───────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5436,
    "dbname":   "trip_db",
    "user":     "admin",
    "password": os.environ["TRIP_DB_PASSWORD"],
}

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
TRIPS_CSV = os.path.join(BASE_DIR, "data", "yellow_tripdata_2015-01_clean.csv")

MILES_TO_KM      = 1.60934
REFERENCE_SPEED  = 12.0   # mph — used for deviation index
SLOW_KMH         = 15.0
FAST_KMH         = 30.0

PAYMENT_MAP = {1: "card", 2: "cash", 3: "no_charge", 4: "dispute"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def classify_time(hour):
    if 7 <= hour <= 9 or 16 <= hour <= 19:
        return "peak"
    elif hour >= 22 or hour < 6:
        return "night"
    else:
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
        speed_mph = dist / (dur / 60.0)
        if speed_mph > 100:
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

# ── Ligação ───────────────────────────────────────────────────────────────────
print("A ligar à base de dados...")
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    print("  → Ligado com sucesso")
except Exception as e:
    print(f"  → Erro ao ligar: {e}")
    sys.exit(1)

# ── Carregar CSV ──────────────────────────────────────────────────────────────
print(f"\nA carregar viagens de '{TRIPS_CSV}'...")

trips = pd.read_csv(TRIPS_CSV, usecols=[
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "pickup_zone_id",
    "pickup_zone_name",
    "dropoff_zone_id",
    "dropoff_zone_name",
    "fare_amount",
    "tip_amount",
    "total_amount",
    "payment_type",
], nrows=10000)  # Remover nrows para o dataset completo

trips["tpep_pickup_datetime"]  = pd.to_datetime(trips["tpep_pickup_datetime"])
trips["tpep_dropoff_datetime"] = pd.to_datetime(trips["tpep_dropoff_datetime"])

trips["trip_duration_min"] = (
    trips["tpep_dropoff_datetime"] - trips["tpep_pickup_datetime"]
).dt.total_seconds() / 60.0

trips["pickup_zone_id"]  = pd.to_numeric(trips["pickup_zone_id"],  errors="coerce")
trips["dropoff_zone_id"] = pd.to_numeric(trips["dropoff_zone_id"], errors="coerce")
trips["trip_distance"]   = pd.to_numeric(trips["trip_distance"],   errors="coerce")
trips["fare_amount"]     = pd.to_numeric(trips["fare_amount"],     errors="coerce")
trips["tip_amount"]      = pd.to_numeric(trips["tip_amount"],      errors="coerce")
trips["passenger_count"] = pd.to_numeric(trips["passenger_count"], errors="coerce")
trips["payment_type"]    = pd.to_numeric(trips["payment_type"],    errors="coerce")

trips = trips.dropna(subset=[
    "tpep_pickup_datetime", "tpep_dropoff_datetime",
    "pickup_zone_id", "dropoff_zone_id",
    "trip_distance", "fare_amount"
])

# ── Enrich ────────────────────────────────────────────────────────────────────
print("A calcular colunas enriquecidas...")

trips["time_class"]       = trips["tpep_pickup_datetime"].dt.hour.apply(classify_time)
trips["trip_distance_km"] = trips["trip_distance"] * MILES_TO_KM

deviation = trips.apply(lambda r: compute_deviation(r["trip_distance"], r["trip_duration_min"]), axis=1)
trips["deviation_index"] = deviation.apply(lambda x: x[0])
trips["deviation_class"] = deviation.apply(lambda x: x[1])

speed = trips.apply(lambda r: compute_speed(r["trip_distance"], r["trip_duration_min"]), axis=1)
trips["avg_speed_kmh"] = speed.apply(lambda x: x[0])
trips["speed_class"]   = speed.apply(lambda x: x[1])

trips["suspicion_score"]   = trips.apply(compute_suspicion, axis=1)
trips["payment_type_str"]  = trips["payment_type"].map(PAYMENT_MAP).fillna("unknown")

trips = trips.where(pd.notnull(trips), other=None)
trips["avg_speed_kmh"] = trips["avg_speed_kmh"].astype(object).where(trips["avg_speed_kmh"].notna(), None)
trips["deviation_index"] = trips["deviation_index"].astype(object).where(trips["deviation_index"].notna(), None)

# ── Insert ────────────────────────────────────────────────────────────────────
cur.execute("TRUNCATE TABLE trips RESTART IDENTITY CASCADE;")

BATCH_SIZE = 1000
records = list(trips[[
    "tpep_pickup_datetime", "tpep_dropoff_datetime",
    "pickup_zone_id", "dropoff_zone_id",
    "pickup_zone_name", "dropoff_zone_name",
    "trip_distance_km", "fare_amount", "tip_amount",
    "passenger_count", "payment_type_str",
    "time_class", "deviation_index", "deviation_class",
    "avg_speed_kmh", "speed_class", "suspicion_score",
]].itertuples(index=False, name=None))

for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i + BATCH_SIZE]
    cur.executemany(
        """
        INSERT INTO trips (
            pickup_datetime, dropoff_datetime,
            pickup_zone_id, dropoff_zone_id,
            pickup_zone_name, dropoff_zone_name,
            trip_distance_km, fare_amount, tip_amount,
            passenger_count, payment_type,
            time_class, deviation_index, deviation_class,
            avg_speed_kmh, speed_class, suspicion_score
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        );
        """,
        batch
    )
    conn.commit()
    print(f"  → {min(i + BATCH_SIZE, len(records))}/{len(records)} viagens inseridas", end="\r")

print(f"\n  → {len(records)} viagens inseridas no total")

cur.close()
conn.close()
print("\nConcluído!")
