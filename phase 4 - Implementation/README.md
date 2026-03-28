# UrbanPulse

## Como correr

**1.** Gerar o CSV limpo com o taxiZoneScript:

python taxiZonesScript/taxiZones.py

**2.** Copiar o ficheiro `yellow_tripdata_2015-01_clean.csv` para a pasta `data/` de cada microserviço. (tem de ser criada à mão por nós)

**3.** Iniciar os containers:

docker compose up --build

**4.** Popular as bases de dados (Abrir um terminal para cada microservice):

python location-service/seed.py
python demand-service/seed.py
python payment-service/seed.py
python trip-service/seed.py

## Para testes, por default os varios seed.py estão limitados a 10 mil linhas. Podemos mudar este valor quando quisermos.

## Portas

| Serviço           | REST | gRPC  | BD   |
| ----------------- | ---- | ----- | ---- |
| Location Service  | 8000 | 50054 | 5433 |
| Demand Service    | 8002 | 50053 | 5434 |
| Payment Service   | 8006 | 50052 | 5435 |
| Trip Service      | 8001 | 50051 | 5436 |
| Analytics Service | 8003 | —     | —    |

## Alguns endpoints para testar:

### Location Service

http://localhost:8000/health
http://localhost:8000/locations/pickup/ranking
http://localhost:8000/locations/161/dropoffs
http://localhost:8000/locations/pairs?min_trips=1
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

### Analytics Service

http://localhost:8003/health
http://localhost:8003/analytics/mobility-comparison
