import pandas as pd
import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://admin:isqueiro20@localhost:5437/location_db"
engine = create_engine(DATABASE_URL)

ZONES_CSV   = "/home/diogocsousa27/taxi_zone_lookup.csv"
TRIPS_CSV   = "/home/diogocsousa27/yellow_tripdata_2015-01_clean.csv"
SAMPLE_ROWS = 10000

# ── Zonas ─────────────────────────────────────────────────────────────────────
print(f"A carregar zonas de '{ZONES_CSV}'...")
zones = pd.read_csv(ZONES_CSV)
zones.columns = zones.columns.str.strip().str.lower()
zones = zones.rename(columns={"locationid": "location_id", "zone": "zone_name"})
zones = zones.dropna(subset=["location_id", "borough", "zone_name", "service_zone"])

with engine.connect() as conn:
    conn.execute(text("TRUNCATE TABLE zones RESTART IDENTITY CASCADE;"))
    conn.commit()

zones[["location_id", "borough", "zone_name", "service_zone"]].to_sql(
    'zones', engine, if_exists='append', index=False
)
print(f"  → {len(zones)} zonas inseridas")

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

with engine.connect() as conn:
    conn.execute(text("TRUNCATE TABLE trips RESTART IDENTITY;"))
    conn.commit()

df_insert = trips[[
    "pickup_date", "pickup_zone_id", "pickup_zone_name",
    "dropoff_zone_id", "dropoff_zone_name",
    "fare_amount", "tip_amount"
]]

print("A inserir dados...")
df_insert.to_sql('trips', engine, if_exists='append', index=False)
print(f"  → {len(df_insert)} viagens inseridas")
print("Concluído!")