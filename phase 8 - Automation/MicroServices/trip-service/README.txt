NOTA (passwords e dependências):
- As passwords das BDs estão no ficheiro .env da pasta "phase 8 - Automation" (copiar .env.example para .env e definir as passwords).
- O docker compose deste serviço tem de ser corrido com: docker compose --env-file ../../.env up --build
- Antes do seed.py: pip install pandas sqlalchemy psycopg2-binary python-dotenv numpy
- Nesta fase, o seed.py lê os CSV da home (~/yellow_tripdata_2015-01_clean.csv e, no location, ~/taxi_zone_lookup.csv).

==============================
  UrbanPulse — Trip Service
  Phase 4 — Guilherme Almeida
==============================

COMO CORRER
-----------

1. Obter o ficheiro CSV limpo:
   Correr o script "taxiZones.py" (pasta taxiZonesScript) para gerar:
     yellow_tripdata_2015-01_clean.csv

2. Criar a pasta "data" dentro de "trip-service" e colocar lá:
     yellow_tripdata_2015-01_clean.csv

3. Subir os containers:
   cd trip-service
   docker compose --env-file ../../.env up --build

4. Seed da base de dados (noutro terminal, após o container estar up):
   python seed.py
   (Limitado a 10 000 viagens para testes — remover "nrows=10000" no seed.py para carga completa)

5. A API fica disponível em: http://localhost:8001


ENDPOINTS
---------

GET  /health
     → Estado do serviço

GET  /trips/classification/time-of-day
     → UC01: Classificação de viagens por período (peak / off_peak / night)
     Parâmetros opcionais: start_date, end_date, pickup_zone_id

GET  /trips/route-deviation
     → UC02: Índice de desvio de rota (efficient / moderate / inefficient)
     Parâmetros opcionais: start_date, end_date, pickup_zone_id, limit, summary_only

GET  /trips/speed/zones
     → UC03: Velocidade média por zona e período (slow / normal / fast)
     Parâmetros opcionais: start_date, end_date, pickup_zone_id, period, limit

GET  /trips/duration-tip-correlation
     → UC18: Correlação entre duração e gorjeta (apenas cartão de crédito)
     Parâmetros opcionais: start_date, end_date, pickup_zone_id

GET  /trips/suspicious
     → UC20: Deteção de viagens com valores suspeitos
     Parâmetros opcionais: start_date, end_date, pickup_zone_id, limit, summary_only

DELETE /trips/invalid/bulk
     → UC21: Remoção em bulk de viagens com dados inválidos
     Parâmetros opcionais: dry_run (true = preview sem apagar)


POST /trips
     → UC22: Submissão de uma nova viagem para análise
     Body JSON com todos os campos obrigatórios (ver /docs)


EXEMPLOS DE TESTE
-----------------

UC01:
  http://localhost:8001/trips/classification/time-of-day
  http://localhost:8001/trips/classification/time-of-day?start_date=2015-01-01&end_date=2015-01-15

UC02:
  http://localhost:8001/trips/route-deviation?summary_only=true
  http://localhost:8001/trips/route-deviation?limit=10

UC03:
  http://localhost:8001/trips/speed/zones?limit=10
  http://localhost:8001/trips/speed/zones?period=peak&limit=5

UC18:
  http://localhost:8001/trips/duration-tip-correlation

UC20:
  http://localhost:8001/trips/suspicious?summary_only=true
  http://localhost:8001/trips/suspicious?limit=20

UC21 (dry run):
  curl -X DELETE "http://localhost:8001/trips/invalid/bulk?dry_run=true"

UC22 (POST example):
  curl -X POST http://localhost:8001/trips \
    -H "Content-Type: application/json" \
    -d '{
      "tpep_pickup_datetime":  "2015-01-10T08:30:00",
      "tpep_dropoff_datetime": "2015-01-10T08:55:00",
      "passenger_count": 2,
      "trip_distance": 3.5,
      "pickup_zone_id": 161,
      "pickup_zone_name": "Midtown Center",
      "dropoff_zone_id": 162,
      "dropoff_zone_name": "Midtown East",
      "fare_amount": 14.50,
      "tip_amount": 3.00,
      "total_amount": 18.80,
      "payment_type": 1
    }'

Documentação interativa (Swagger UI):
  http://localhost:8001/docs

