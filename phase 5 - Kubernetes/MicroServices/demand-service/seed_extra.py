import psycopg2
import numpy as np
import pandas as pd
import calendar
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

ZONE_IDS = [161, 162, 163, 164, 230, 186, 87, 88, 137, 141, 79, 211, 234, 237, 239]

MONTHS = {
    (2015, 2):  800,
    (2015, 3):  950,
    (2015, 4):  900,
    (2015, 6):  1100,
    (2015, 9):  850,
    (2015, 12): 700,
    (2016, 1):  750,
    (2016, 6):  1000,
    (2016, 12): 680,
}

np.random.seed(42)

# Pesos normalizados correctamente
hour_w = np.array([0.3,0.2,0.15,0.1,0.1,0.2,0.5,0.9,1.0,0.8,0.7,0.8,
                   0.9,0.8,0.7,0.7,0.8,1.0,1.0,0.9,0.8,0.7,0.6,0.4])
hour_w = hour_w / hour_w.sum()

dow_w = np.array([1.0,1.0,1.0,1.0,1.1,0.8,0.7])
dow_w = dow_w / dow_w.sum()

records = []
for (year, month), n_trips in MONTHS.items():
    days_in_month = calendar.monthrange(year, month)[1]
    hours = np.random.choice(range(24), size=n_trips, p=hour_w)
    dows  = np.random.choice(range(7),  size=n_trips, p=dow_w)
    days  = np.random.randint(1, days_in_month + 1, size=n_trips)
    zones = np.random.choice(ZONE_IDS, size=n_trips)
    mins  = np.random.randint(0, 60, size=n_trips)

    for i in range(n_trips):
        dt = pd.Timestamp(year=year, month=month, day=int(days[i]),
                          hour=int(hours[i]), minute=int(mins[i]))
        records.append((int(zones[i]), dt, year, month, int(dows[i]), int(hours[i])))

print(f"  → {len(records)} viagens geradas em {len(MONTHS)} meses")

print(f"A ligar a {DB_CONFIG['dbname']} (porta {DB_CONFIG['port']})...")
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()
    print("  → Ligado com sucesso")
except Exception as e:
    print(f"  → Erro: {e}")
    sys.exit(1)

cur.executemany(
    """
    INSERT INTO trips (
        pickup_zone_id, pickup_datetime,
        pickup_year, pickup_month,
        pickup_day_of_week, pickup_hour
    ) VALUES (%s, %s, %s, %s, %s, %s)
    """,
    records
)
conn.commit()
print(f"  → {len(records)} viagens inseridas")
cur.close()
conn.close()
print("Concluído!")
