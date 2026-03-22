# UrbanPulse — Revenue & Demand Services

## Arquitetura

```
revenue-service (8001) ──→ db-revenue (5432)  [revenue_db]
demand-service  (8002) ──→ db-demand  (5433)  [demand_db]
```

Cada microserviço tem a sua própria base de dados PostgreSQL isolada.
Ambas as BDs têm o mesmo schema e os mesmos dados de viagens.

## Estrutura do projecto

```
phase4/
├── docker-compose.yml
├── db/
│   ├── 01_schema.sql       ← Schema (tabelas + índices)
│   ├── 02_seed.sql         ← Dados sintéticos para desenvolvimento
│   └── 03_transform.sql    ← Transformação dados reais: trips_raw → trips
├── revenue-service/        ← UC08, UC09, UC10  (porta 8001)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── db/
│       │   ├── __init__.py
│       │   └── connection.py   ← liga a db-revenue:5432
│       └── routers/
│           ├── __init__.py
│           ├── avg_fare.py     ← UC08
│           ├── breakdown.py    ← UC09
│           └── fare_per_km.py  ← UC10
└── demand-service/         ← UC15, UC16  (porta 8002)
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── __init__.py
        ├── main.py
        ├── db/
        │   ├── __init__.py
        │   └── connection.py   ← liga a db-demand:5433
        └── routers/
            ├── __init__.py
            ├── hourly_matrix.py  ← UC15
            └── monthly_trend.py  ← UC16
```

---

## Ordem de execução

### Opção A — Desenvolvimento (dados sintéticos)

```bash
docker compose up --build
```

Isto faz tudo automaticamente:
- Cria db-revenue e db-demand (dois PostgreSQL isolados)
- Corre 01_schema.sql e 02_seed.sql em cada uma
- Arranca Revenue Service na porta 8001
- Arranca Demand Service na porta 8002

Pronto. Acede em: http://localhost:8001/docs e http://localhost:8002/docs


### Opção B — Produção (CSVs reais do Kaggle)

#### Passo 1 — Arrancar os containers
```bash
docker compose up --build
```

#### Passo 2 — Copiar os CSVs para ambos os containers

```bash
# Para a BD do Revenue Service
docker cp yellow_tripdata_2015-01.csv urbanpulse-db-revenue:/tmp/
docker cp yellow_tripdata_2015-02.csv urbanpulse-db-revenue:/tmp/
# ... repetir para cada ficheiro

# Para a BD do Demand Service (mesmos ficheiros)
docker cp yellow_tripdata_2015-01.csv urbanpulse-db-demand:/tmp/
docker cp yellow_tripdata_2015-02.csv urbanpulse-db-demand:/tmp/
# ... repetir para cada ficheiro
```

#### Passo 3 — Carregar CSVs para trips_raw em cada BD

```bash
# Revenue DB
docker exec -it urbanpulse-db-revenue psql -U urbanpulse -d revenue_db

# Demand DB
docker exec -it urbanpulse-db-demand psql -U urbanpulse -d demand_db
```

Dentro do psql (repetir para cada ficheiro e em cada BD):
```sql
COPY trips_raw (
    "VendorID", tpep_pickup_datetime, tpep_dropoff_datetime,
    passenger_count, trip_distance,
    pickup_longitude, pickup_latitude, "RateCodeID", store_and_fwd_flag,
    dropoff_longitude, dropoff_latitude,
    payment_type, fare_amount, extra, mta_tax, tip_amount,
    tolls_amount, improvement_surcharge, total_amount
)
FROM '/tmp/yellow_tripdata_2015-01.csv'
CSV HEADER;
```

#### Passo 4 — Transformar trips_raw → trips em cada BD

```bash
# Revenue DB
docker cp db/03_transform.sql urbanpulse-db-revenue:/tmp/
docker exec -it urbanpulse-db-revenue psql -U urbanpulse -d revenue_db -f /tmp/03_transform.sql

# Demand DB
docker cp db/03_transform.sql urbanpulse-db-demand:/tmp/
docker exec -it urbanpulse-db-demand psql -U urbanpulse -d demand_db -f /tmp/03_transform.sql
```

---

## Endpoints

### Revenue Service — http://localhost:8001/docs

| Endpoint | UC | Descrição |
|----------|----|-----------|
| GET `/revenue/avg-fare-by-zone` | UC08 | Tarifa média por zona com desvio face à média global |
| GET `/revenue/breakdown` | UC09 | Decomposição percentual da receita por viagem |
| GET `/revenue/fare-per-km` | UC10 | Preço por km por zona |

### Demand Service — http://localhost:8002/docs

| Endpoint | UC | Descrição |
|----------|----|-----------|
| GET `/demand/hourly-matrix` | UC15 | Matriz hora × dia com horas de ponta |
| GET `/demand/monthly-trend` | UC16 | Evolução mensal com variação percentual |

---

## Exemplos de chamadas

```bash
# UC08 — Top 5 zonas com tarifa mais alta em Junho 2015
curl "http://localhost:8001/revenue/avg-fare-by-zone?year=2015&month=6&sort=desc&limit=5"

# UC09 — Decomposição de receita para zona 161 (Midtown Center)
curl "http://localhost:8001/revenue/breakdown?zone_id=161&year=2015"

# UC10 — Preço por km, top 10 zonas de dropoff
curl "http://localhost:8001/revenue/fare-per-km?zone_type=dropoff&sort=desc&limit=10"

# UC15 — Matriz hora × dia global para 2015
curl "http://localhost:8002/demand/hourly-matrix?year=2015"

# UC16 — Evolução mensal 2015-2016, comparação mês a mês
curl "http://localhost:8002/demand/monthly-trend?year_from=2015&year_to=2016&compare_by=month"
```

---

## Parar / limpar

```bash
# Parar (mantém os dados das BDs)
docker compose down

# Parar e apagar ambas as BDs (recomeçar do zero)
docker compose down -v
```
