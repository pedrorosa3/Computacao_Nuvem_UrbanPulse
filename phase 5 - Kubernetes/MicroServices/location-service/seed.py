import psycopg2
import pandas as pd
import sys
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

# ── Config ───────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5437,
    "dbname":   "location_db",
    "user":     "admin",
    "password": os.environ["LOCATION_DB_PASSWORD"],
}

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ZONES_CSV  = "/home/diogocsousa27/taxi_zone_lookup.csv"
TRIPS_CSV  = "/home/diogocsousa27/yellow_tripdata_2015-01_clean.csv"

# Limite de viagens para testes (remover para inserir tudo)
SAMPLE_ROWS = 10000

# ── Ligação ───────────────────────────────────────────────────────────────────
print("A ligar à base de dados...")
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    print("  → Ligado com sucesso")
except Exception as e:
    print(f"  → Erro ao ligar: {e}")
    sys.exit(1)

# ── Zonas ─────────────────────────────────────────────────────────────────────
print(f"\nA carregar zonas de '{ZONES_CSV}'...")
zones = pd.read_csv(ZONES_CSV)
zones.columns = zones.columns.str.strip().str.lower()

cur.execute("TRUNCATE TABLE zones RESTART IDENTITY CASCADE;")

inserted = 0
for _, row in zones.iterrows():
    cur.execute(
        """
        INSERT INTO zones (location_id, borough, zone_name, service_zone)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (location_id) DO NOTHING;
        """,
        (int(row["locationid"]), row["borough"], row["zone"], row["service_zone"])
    )
    inserted += 1

conn.commit()
print(f"  → {inserted} zonas inseridas")

# ── Trips ─────────────────────────────────────────────────────────────────────
print(f"\nA carregar viagens de '{TRIPS_CSV}'...")
trips = pd.read_csv(TRIPS_CSV, usecols=[
    "tpep_pickup_datetime",
    "pickup_zone_id",
    "pickup_zone_name",
    "dropoff_zone_id",
    "dropoff_zone_name",
    "fare_amount",
    "tip_amount",
], nrows=SAMPLE_ROWS)

trips = trips.dropna(subset=["pickup_zone_id", "dropoff_zone_id"])
trips["pickup_date"]       = pd.to_datetime(trips["tpep_pickup_datetime"]).dt.date
trips["pickup_zone_id"]    = trips["pickup_zone_id"].astype(int)
trips["dropoff_zone_id"]   = trips["dropoff_zone_id"].astype(int)
trips["pickup_zone_name"]  = trips["pickup_zone_name"].astype(str)
trips["dropoff_zone_name"] = trips["dropoff_zone_name"].astype(str)
trips["fare_amount"]       = trips["fare_amount"].fillna(0)
trips["tip_amount"]        = trips["tip_amount"].fillna(0)

cur.execute("TRUNCATE TABLE trips RESTART IDENTITY;")

BATCH_SIZE = 1000
records = list(trips[[
    "pickup_date", "pickup_zone_id", "pickup_zone_name",
    "dropoff_zone_id", "dropoff_zone_name",
    "fare_amount", "tip_amount"
]].itertuples(index=False, name=None))

for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i + BATCH_SIZE]
    cur.executemany(
        """
        INSERT INTO trips (
            pickup_date, pickup_zone_id, pickup_zone_name,
            dropoff_zone_id, dropoff_zone_name,
            fare_amount, tip_amount
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """,
        batch
    )
    conn.commit()
    print(f"  → {min(i + BATCH_SIZE, len(records))}/{len(records)} viagens inseridas", end="\r")

print(f"\n  → {len(records)} viagens inseridas no total")

cur.close()
conn.close()
print("\nConcluído!")