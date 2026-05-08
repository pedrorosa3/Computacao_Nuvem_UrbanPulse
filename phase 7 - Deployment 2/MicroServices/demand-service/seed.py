import pandas as pd
import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://urbanpulse:urbanpulse@localhost:5434/demand_db"
engine = create_engine(DATABASE_URL)

TRIPS_CSV   = "/home/diogocsousa27/yellow_tripdata_2015-01_clean.csv"
SAMPLE_ROWS = 10000

print(f"A carregar viagens de '{TRIPS_CSV}'...")
trips = pd.read_csv(TRIPS_CSV, usecols=[
    "tpep_pickup_datetime",
    "pickup_zone_id",
], nrows=SAMPLE_ROWS)

trips = trips.dropna(subset=["pickup_zone_id", "tpep_pickup_datetime"])
trips["pickup_zone_id"]  = trips["pickup_zone_id"].astype(int)
trips["pickup_datetime"] = pd.to_datetime(trips["tpep_pickup_datetime"])

trips["pickup_year"]        = trips["pickup_datetime"].dt.year
trips["pickup_month"]       = trips["pickup_datetime"].dt.month
trips["pickup_day_of_week"] = trips["pickup_datetime"].dt.dayofweek
trips["pickup_hour"]        = trips["pickup_datetime"].dt.hour

with engine.connect() as conn:
    conn.execute(text("TRUNCATE TABLE trips RESTART IDENTITY;"))
    conn.commit()

df_insert = trips[[
    "pickup_zone_id", "pickup_datetime",
    "pickup_year", "pickup_month",
    "pickup_day_of_week", "pickup_hour"
]]

print("A inserir dados...")
df_insert.to_sql('trips', engine, if_exists='append', index=False)
print(f"  → {len(df_insert)} viagens inseridas")
print("Concluído!")