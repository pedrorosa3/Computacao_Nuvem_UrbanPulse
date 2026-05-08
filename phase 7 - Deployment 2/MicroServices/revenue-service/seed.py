import pandas as pd
import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://urbanpulse:urbanpulse@localhost:5433/revenue_db"
engine = create_engine(DATABASE_URL)

TRIPS_CSV   = "/home/diogocsousa27/yellow_tripdata_2015-01_clean.csv"
SAMPLE_ROWS = 10000

print(f"A carregar viagens de '{TRIPS_CSV}'...")
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

with engine.connect() as conn:
    conn.execute(text("TRUNCATE TABLE trips RESTART IDENTITY;"))
    conn.commit()

df_insert = trips[[
    "pickup_date", "pickup_zone_id", "dropoff_zone_id",
    "fare_amount", "tip_amount", "tolls_amount",
    "mta_tax", "improvement_surcharge", "extra", "total_amount"
]]

print("A inserir dados...")
df_insert.to_sql('trips', engine, if_exists='append', index=False)
print(f"  → {len(df_insert)} viagens inseridas")
print("Concluído!")