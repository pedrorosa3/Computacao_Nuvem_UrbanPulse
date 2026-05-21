import os
import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://admin:password@localhost:5435/payment_db"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Verificar se a coluna id existe
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='trips' AND column_name='id'
    """))
    has_id = result.fetchone() is not None

    if not has_id:
        # Tabela não existe ou existe sem id — apagar e recriar
        conn.execute(text("DROP TABLE IF EXISTS trips"))
        conn.execute(text("""
            CREATE TABLE trips (
                id SERIAL PRIMARY KEY,
                pickup_date DATE NOT NULL,
                pickup_zone_id INTEGER NOT NULL,
                payment_type VARCHAR NOT NULL,
                fare_amount FLOAT NOT NULL,
                tip_amount FLOAT DEFAULT 0,
                passenger_count INTEGER
            )
        """))
        conn.commit()
        print("Tabela recriada com schema correto.")
    else:
        # Tabela existe com id — limpar dados anteriores
        conn.execute(text("TRUNCATE TABLE trips RESTART IDENTITY"))
        conn.commit()
        print("Tabela limpa, pronta para novo seed.")

TRIPS_CSV = os.path.join(os.path.expanduser("~"), "yellow_tripdata_2015-01_clean.csv")

print("A ler o dataset...")
df = pd.read_csv(TRIPS_CSV, nrows=10000)

payment_map = {1: 'card', 2: 'cash', 3: 'no_charge', 4: 'dispute', 5: 'unknown', 6: 'voided'}
df['payment_type'] = df['payment_type'].map(payment_map).fillna('unknown')
df['pickup_date'] = pd.to_datetime(df['tpep_pickup_datetime']).dt.date

df_payments = df[[
    'pickup_date',
    'pickup_zone_id',
    'payment_type',
    'fare_amount',
    'tip_amount',
    'passenger_count'
]]

print("A inserir dados na base de dados (payment-db)...")
df_payments.to_sql('trips', engine, if_exists='append', index=False)
print("Seed concluído com sucesso!")