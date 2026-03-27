import psycopg2
import pandas as pd
import sys
import os
import numpy as np

# ── Config ───────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5434,
    "dbname":   "trip_db",
    "user":     "admin",
    "password": "isqueiro20",
}

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
TRIPS_CSV = os.path.join(BASE_DIR, "data", "yellow_tripdata_2015-01_clean.csv")

# ── Ligação ───────────────────────────────────────────────────────────────────
print("A ligar à base de dados...")
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    print("  → Ligado com sucesso")
except Exception as e:
    print(f"  → Erro ao ligar: {e}")
    sys.exit(1)

# ── Trips ─────────────────────────────────────────────────────────────────────
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
], nrows=10000)  # Remover nrows para inserir o dataset completo

# Limpar dados
trips = trips.dropna(subset=["tpep_pickup_datetime", "tpep_dropoff_datetime"])
trips["tpep_pickup_datetime"]  = pd.to_datetime(trips["tpep_pickup_datetime"])
trips["tpep_dropoff_datetime"] = pd.to_datetime(trips["tpep_dropoff_datetime"])

# Calcular duração em minutos
trips["trip_duration_min"] = (
    trips["tpep_dropoff_datetime"] - trips["tpep_pickup_datetime"]
).dt.total_seconds() / 60.0

# Converter tipos
trips["pickup_zone_id"]   = pd.to_numeric(trips["pickup_zone_id"],   errors="coerce")
trips["dropoff_zone_id"]  = pd.to_numeric(trips["dropoff_zone_id"],  errors="coerce")
trips["trip_distance"]    = pd.to_numeric(trips["trip_distance"],    errors="coerce")
trips["fare_amount"]      = pd.to_numeric(trips["fare_amount"],      errors="coerce")
trips["tip_amount"]       = pd.to_numeric(trips["tip_amount"],       errors="coerce")
trips["total_amount"]     = pd.to_numeric(trips["total_amount"],     errors="coerce")
trips["passenger_count"]  = pd.to_numeric(trips["passenger_count"],  errors="coerce")
trips["payment_type"]     = pd.to_numeric(trips["payment_type"],     errors="coerce")

# Substituir NaN por None (NULL no SQL)
trips = trips.where(pd.notnull(trips), None)

cur.execute("TRUNCATE TABLE trips RESTART IDENTITY;")

BATCH_SIZE = 1000
records = list(trips[[
    "tpep_pickup_datetime", "tpep_dropoff_datetime",
    "passenger_count", "trip_distance",
    "pickup_zone_id", "pickup_zone_name",
    "dropoff_zone_id", "dropoff_zone_name",
    "fare_amount", "tip_amount", "total_amount",
    "payment_type", "trip_duration_min"
]].itertuples(index=False, name=None))

for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i + BATCH_SIZE]
    cur.executemany(
        """
        INSERT INTO trips (
            tpep_pickup_datetime, tpep_dropoff_datetime,
            passenger_count, trip_distance,
            pickup_zone_id, pickup_zone_name,
            dropoff_zone_id, dropoff_zone_name,
            fare_amount, tip_amount, total_amount,
            payment_type, trip_duration_min
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        batch
    )
    conn.commit()
    print(f"  → {min(i + BATCH_SIZE, len(records))}/{len(records)} viagens inseridas", end="\r")

print(f"\n  → {len(records)} viagens inseridas no total")

cur.close()
conn.close()
print("\nConcluído!")
