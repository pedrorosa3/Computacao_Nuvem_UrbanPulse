import psycopg2
import pandas as pd
import sys
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

# ── Config ───────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5434,
    "dbname":   "demand_db",
    "user":     "urbanpulse",
    "password": os.environ["DEMAND_DB_PASSWORD"],
}

TRIPS_CSV = os.path.join(os.path.expanduser("~"), "yellow_tripdata_2015-01_clean.csv")
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
], nrows=SAMPLE_ROWS)

trips = trips.dropna(subset=["pickup_zone_id", "tpep_pickup_datetime"])
trips["pickup_zone_id"]  = trips["pickup_zone_id"].astype(int)
trips["pickup_datetime"] = pd.to_datetime(trips["tpep_pickup_datetime"])

# Pré-calcular colunas derivadas
trips["pickup_year"]        = trips["pickup_datetime"].dt.year
trips["pickup_month"]       = trips["pickup_datetime"].dt.month
trips["pickup_day_of_week"] = trips["pickup_datetime"].dt.dayofweek  # 0=Segunda, 6=Domingo
trips["pickup_hour"]        = trips["pickup_datetime"].dt.hour

cur.execute("TRUNCATE TABLE trips RESTART IDENTITY;")

BATCH_SIZE = 1000
records = list(trips[[
    "pickup_zone_id", "pickup_datetime",
    "pickup_year", "pickup_month",
    "pickup_day_of_week", "pickup_hour"
]].itertuples(index=False, name=None))

for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i + BATCH_SIZE]
    cur.executemany(
        """
        INSERT INTO trips (
            pickup_zone_id, pickup_datetime,
            pickup_year, pickup_month,
            pickup_day_of_week, pickup_hour
        )
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        batch
    )
    conn.commit()
    print(f"  → {min(i + BATCH_SIZE, len(records))}/{len(records)} viagens inseridas", end="\r")

print(f"\n  → {len(records)} viagens inseridas no total")

cur.close()
conn.close()
print("\nConcluído!")
