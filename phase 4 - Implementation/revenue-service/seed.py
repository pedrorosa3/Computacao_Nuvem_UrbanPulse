import psycopg2
import pandas as pd
import sys
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# ── Config ───────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5433,
    "dbname":   "revenue_db",
    "user":     "urbanpulse",
    "password": os.environ["REVENUE_DB_PASSWORD"],
}

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
TRIPS_CSV = os.path.join(BASE_DIR, "data", "yellow_tripdata_2015-01_clean.csv")

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

# ── Trips ─────────────────────────────────────────────────────────────────────
print(f"\nA carregar viagens de '{TRIPS_CSV}'...")
trips = pd.read_csv(TRIPS_CSV, usecols=[
    "tpep_pickup_datetime",
    "pickup_zone_id",
    "dropoff_zone_id",
    "fare_amount",
    "tip_amount",
    "tolls_amount",
    "mta_tax",
    "improvement_surcharge",
    "extra",
    "total_amount",
], nrows=SAMPLE_ROWS)

trips = trips.dropna(subset=["pickup_zone_id", "dropoff_zone_id", "fare_amount", "total_amount"])
trips["pickup_date"]           = pd.to_datetime(trips["tpep_pickup_datetime"]).dt.date
trips["pickup_zone_id"]        = trips["pickup_zone_id"].astype(int)
trips["dropoff_zone_id"]       = trips["dropoff_zone_id"].astype(int)
trips["tip_amount"]            = trips["tip_amount"].fillna(0)
trips["tolls_amount"]          = trips["tolls_amount"].fillna(0)
trips["mta_tax"]               = trips["mta_tax"].fillna(0)
trips["improvement_surcharge"] = trips["improvement_surcharge"].fillna(0)
trips["extra"]                 = trips["extra"].fillna(0)

cur.execute("TRUNCATE TABLE trips RESTART IDENTITY;")

BATCH_SIZE = 1000
records = list(trips[[
    "pickup_date", "pickup_zone_id", "dropoff_zone_id",
    "fare_amount", "tip_amount", "tolls_amount",
    "mta_tax", "improvement_surcharge", "extra", "total_amount"
]].itertuples(index=False, name=None))

for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i + BATCH_SIZE]
    cur.executemany(
        """
        INSERT INTO trips (
            pickup_date, pickup_zone_id, dropoff_zone_id,
            fare_amount, tip_amount, tolls_amount,
            mta_tax, improvement_surcharge, extra, total_amount
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        batch
    )
    conn.commit()
    print(f"  → {min(i + BATCH_SIZE, len(records))}/{len(records)} viagens inseridas", end="\r")

print(f"\n  → {len(records)} viagens inseridas no total")

cur.close()
conn.close()
print("\nConcluído!")