import pandas as pd
from sqlalchemy import create_engine

# URL de ligação à DB através do teu PC local (porta 5434)
DATABASE_URL = "postgresql://admin:password@localhost:5435/payment_db"
engine = create_engine(DATABASE_URL)

print("A ler o dataset...")
df = pd.read_csv("/home/diogocsousa27/yellow_tripdata_2015-01_clean.csv", nrows=10000)

# Mapear os IDs de pagamento do dataset original para texto
payment_map = {1: 'card', 2: 'cash', 3: 'no_charge', 4: 'dispute', 5: 'unknown', 6: 'voided'}
df['payment_type'] = df['payment_type'].map(payment_map).fillna('unknown')

# Converter a data/hora para apenas Data (DATE) como definiste no esquema
df['pickup_date'] = pd.to_datetime(df['tpep_pickup_datetime']).dt.date

# Selecionar apenas as colunas que interessam para o Payment Service
# Agora usamos 'pickup_zone_id' porque o teu script taxiZones.py já a criou com esse nome!
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