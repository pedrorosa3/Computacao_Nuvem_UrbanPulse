import pandas as pd
import geopandas as gpd
import os


#Config
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))

TRIPS_FILE  = os.path.join(BASE_DIR, "yellow_tripdata_2015-01.csv")
ZONES_FILE  = os.path.join(BASE_DIR, "taxi_zones.shp")
OUTPUT_FILE = os.path.join(BASE_DIR, "yellow_tripdata_2015-01_clean.csv")

#Quando quisermos correr o ficheiro todo, colocar a None
SAMPLE_ROWS  = None


print("A carregar zonas...")
zones = gpd.read_file(ZONES_FILE)
zones = zones[["LocationID", "zone", "borough", "geometry"]].copy()
zones = zones.to_crs("EPSG:4326")

print(f"A carregar viagens ({SAMPLE_ROWS or 'todas'} linhas)...")
trips = pd.read_csv(TRIPS_FILE, nrows=SAMPLE_ROWS)

# Remove coordenadas inválidas
print("A limpar coordenadas inválidas...")
trips = trips[
    (trips["pickup_longitude"].between(-74.3, -73.7)) &
    (trips["pickup_latitude"].between(40.5, 40.9)) &
    (trips["dropoff_longitude"].between(-74.3, -73.7)) &
    (trips["dropoff_latitude"].between(40.5, 40.9))
].copy()
print(f"  → {len(trips)} viagens com coordenadas válidas")

# ── PICKUP ZONE
print("A calcular pickup zones...")
pickup_points = gpd.GeoDataFrame(
    trips[["pickup_longitude", "pickup_latitude"]],
    geometry=gpd.points_from_xy(trips["pickup_longitude"], trips["pickup_latitude"]),
    crs="EPSG:4326"
)
pickup_joined = gpd.sjoin(
    pickup_points,
    zones[["LocationID", "zone", "geometry"]],
    how="left",
    predicate="within"
)
trips["pickup_zone_id"]   = pickup_joined["LocationID"].values
trips["pickup_zone_name"] = pickup_joined["zone"].values

# ── DROPOFF ZONE
print("A calcular dropoff zones...")
dropoff_points = gpd.GeoDataFrame(
    trips[["dropoff_longitude", "dropoff_latitude"]],
    geometry=gpd.points_from_xy(trips["dropoff_longitude"], trips["dropoff_latitude"]),
    crs="EPSG:4326"
)
dropoff_joined = gpd.sjoin(
    dropoff_points,
    zones[["LocationID", "zone", "geometry"]],
    how="left",
    predicate="within"
)
trips["dropoff_zone_id"]   = dropoff_joined["LocationID"].values
trips["dropoff_zone_name"] = dropoff_joined["zone"].values

#Result
trips_clean = trips.dropna(subset=["pickup_zone_id", "dropoff_zone_id"])
print(f"  → {len(trips_clean)} viagens com zonas identificadas ({len(trips) - len(trips_clean)} sem zona)")

print(f"A guardar em {OUTPUT_FILE}...")
trips_clean.to_csv(OUTPUT_FILE, index=False)
print("Concluído!")

# Mostra uma amostra do resultado
print("\nAmostra do resultado:")
print(trips_clean[["tpep_pickup_datetime", "pickup_zone_id", "pickup_zone_name",
                    "dropoff_zone_id", "dropoff_zone_name", "fare_amount"]].head(10))