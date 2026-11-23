# UrbanPulse

## Link para fazer download do dataset:

https://www.kaggle.com/datasets/elemento/nyc-yellow-taxi-trip-data

## Como colocar o projeto a funcionar

**1.** Gerar o CSV limpo com o taxiZoneScript:

python taxiZonesScript/taxiZones.py

**2.** Copiar o ficheiro `yellow_tripdata_2015-01_clean.csv` para a pasta `data/` de cada microserviço. (tem de ser criada à mão por nós, o analytics não tem esta pasta, e o location service deve conter também o "taxi_zone_lookup.csv".)

**3.** Criar o ficheiro `.env` com as passwords das bases de dados (nesta pasta):

cp .env.example .env

Editar o `.env` e definir as passwords. O ficheiro está no `.gitignore` e nunca deve ser commitado.

**4.** Iniciar os containers:

docker compose up --build

**5.** Instalar as dependências dos seeds e popular as bases de dados (com os containers a correr):

pip install pandas sqlalchemy psycopg2-binary python-dotenv numpy

python location-service/seed.py
python demand-service/seed.py
python demand-service/seed_extra.py
python payment-service/seed.py
python trip-service/seed.py
python revenue-service/seed.py

**Nota:** o Postgres só lê a password na primeira vez que cria a base de dados. Se mudares as passwords no `.env` depois de já teres corrido o projeto, apaga as pastas `*/db-data/` antes de voltar a arrancar. Caso contrário, os seeds falham com `password authentication failed`.

## Para testes, por default os varios seed.py estão limitados a 10 mil linhas. Podemos mudar este valor quando quisermos.

## Portas

| Serviço           | REST | gRPC  | BD   |
| ----------------- | ---- | ----- | ---- |
| Location Service  | 8000 | 50054 | 5437 |
| Demand Service    | 8002 | 50053 | 5434 |
| Payment Service   | 8006 | 50052 | 5435 |
| Trip Service      | 8001 | 50051 | 5436 |
| Revenue Service   | 8007 | 50055 | 5433 |
| Analytics Service | 8003 | —     | —    |

**Nota:** Se ao correr o projeto algum serviço falhar com erro de ligação à base de dados, é provável que a porta configurada já esteja em uso no pc.
Nesse caso, altera a porta do serviço afetado no `docker-compose.yml` global, no `docker-compose.yml` individual do serviço e no respetivo `seed.py`,garantindo que os três ficheiros usam sempre a mesma porta.

## Alguns endpoints para testar:

### Location Service

http://localhost:8000/health
http://localhost:8000/locations/pickup/ranking
http://localhost:8000/locations/161/dropoffs
http://localhost:8000/locations/pairs?min_trips=100
http://localhost:8000/locations/161/profile
http://localhost:8000/locations/zones

### Demand Service

http://localhost:8002/health
http://localhost:8002/demand/hourly-matrix?year=2015
http://localhost:8002/demand/monthly-trend?year_from=2015
http://localhost:8002/demand/zone-volatility?zone_id=161

### Payment Service

http://localhost:8006/api/v1/payments/distribution
http://localhost:8006/api/v1/payments/tips/comparison
http://localhost:8006/api/v1/payments/zones/tipping-score

### Trip Service

http://localhost:8001/health
http://localhost:8001/trips/classification/time-of-day
http://localhost:8001/trips/route-deviation?summary_only=true
http://localhost:8001/trips/speed/zones

### Revenue Service

http://localhost:8007/health
http://localhost:8007/revenue/avg-fare-by-zone
http://localhost:8007/revenue/breakdown
http://localhost:8007/revenue/breakdown?zone_id=161&year=2015
http://localhost:8007/revenue/fare-per-km
http://localhost:8007/revenue/fare-per-km?sort=asc&limit=5

### Analytics Service

http://localhost:8003/health
http://localhost:8003/analytics/mobility-comparison
