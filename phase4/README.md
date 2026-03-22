# UrbanPulse — Revenue & Demand Services

## Estrutura do projecto

```
urbanpulse/
├── docker-compose.yml
├── db/
│   ├── 01_schema.sql       ← Schema da BD (tabelas + índices)
│   ├── 02_seed.sql         ← Dados sintéticos para desenvolvimento
│   └── 03_transform.sql    ← Transformação dados reais: trips_raw → trips
├── revenue-service/        ← UC08, UC09, UC10  (porta 8001)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── db/connection.py
│       └── routers/
│           ├── avg_fare.py      ← UC08
│           ├── breakdown.py     ← UC09
│           └── fare_per_km.py   ← UC10
└── demand-service/         ← UC15, UC16  (porta 8002)
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── main.py
        ├── db/connection.py
        └── routers/
            ├── hourly_matrix.py  ← UC15
            └── monthly_trend.py  ← UC16
```

---

## Ordem de execução

### Opção A — Desenvolvimento (dados sintéticos, arranque rápido)

```
1.  docker compose up --build
```

Isto faz tudo automaticamente:
- Arranca o PostgreSQL
- Corre 01_schema.sql  (cria as tabelas)
- Corre 02_seed.sql    (insere ~17k viagens sintéticas)
- Arranca Revenue Service (porta 8001)
- Arranca Demand Service  (porta 8002)

Pronto. Testa em: http://localhost:8001/docs e http://localhost:8002/docs


### Opção B — Produção (com os CSVs reais do Kaggle)

#### Passo 1 — Arrancar os containers (sem seed de dados)

Se não quiseres os dados sintéticos, comenta a linha do 02_seed.sql
no docker-compose.yml antes de arrancar:

```bash
docker compose up --build
```

#### Passo 2 — Copiar os CSVs para dentro do container da BD

```bash
docker cp /caminho/local/yellow_tripdata_2015-01.csv urbanpulse-db:/tmp/
docker cp /caminho/local/yellow_tripdata_2015-02.csv urbanpulse-db:/tmp/
# ... repetir para cada ficheiro
```

#### Passo 3 — Carregar cada CSV para trips_raw (staging)

```bash
docker exec -it urbanpulse-db psql -U urbanpulse -d urbanpulse
```

Dentro do psql, por cada ficheiro:

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

Repetir para cada um dos 4 ficheiros (2015-01 a 2016-12).

#### Passo 4 — Transformar trips_raw → trips (resolve lat/lon para zone IDs)

```bash
docker exec -it urbanpulse-db psql -U urbanpulse -d urbanpulse \
  -f /docker-entrypoint-initdb.d/03_transform.sql
```

Ou se não montaste o ficheiro, copia-o primeiro:

```bash
docker cp db/03_transform.sql urbanpulse-db:/tmp/
docker exec -it urbanpulse-db psql -U urbanpulse -d urbanpulse -f /tmp/03_transform.sql
```

Este passo pode demorar vários minutos com os dados reais (7GB).

---

## Endpoints disponíveis

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

# UC16 — Comparação com o mesmo mês do ano anterior
curl "http://localhost:8002/demand/monthly-trend?year_from=2015&year_to=2016&compare_by=year"
```

---

## Parar / limpar

```bash
# Parar (mantém dados da BD)
docker compose down

# Parar e apagar tudo (BD incluída)
docker compose down -v
```
