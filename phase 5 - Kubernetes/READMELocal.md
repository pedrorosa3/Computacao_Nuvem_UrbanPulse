Indicações para correr o kubernetes localmente

### 1. Ir para a pasta do projeto

cd "<pasta do repositório>\phase 5 - Kubernetes\MicroServices"

### 2. Criar o namespace

kubectl create namespace urbanpulse

### 2.1 Criar os Secrets

Criar os Secrets com as passwords das DBs, a partir do `.env` da pasta `phase 5 - Kubernetes` (criado a partir do `.env.example`):

```bash
ENV_FILE="../.env" bash "../kubernetesCloud/create-secrets.sh"
```

### 3. Criar os ConfigMaps do init.sql (Location e Trip)

kubectl create configmap location-db-init --from-file=init.sql=./location-service/db/init.sql -n urbanpulse
kubectl create configmap trip-db-init --from-file=init.sql=./trip-service/db/init.sql -n urbanpulse

### 4. Build das imagens necessárias

docker build -t location-api:latest ./location-service
docker build -t trip-api:latest ./trip-service
docker build -t analytics-api:latest ./analytics-service

### 5. Aplicar os yamls

kubectl apply -f "../kubernetesLocal/location-service/"
kubectl apply -f "../kubernetesLocal/trip-service/"
kubectl apply -f "../kubernetesLocal/analytics-service/"

### 6. Verificar que os pods estão a correr

kubectl get pods -n urbanpulse

### 7. Popular a base de dados (seed)

> Antes do seed: `pip install pandas sqlalchemy psycopg2-binary python-dotenv numpy`. O `seed.py` lê a password do `.env` da pasta `phase 5 - Kubernetes` e os CSV da home (`~/yellow_tripdata_2015-01_clean.csv` e `~/taxi_zone_lookup.csv`).

**Expor as BDs** (cada uma num terminal)
kubectl port-forward svc/location-db 5437:5432 -n urbanpulse
kubectl port-forward svc/trip-db 5436:5432 -n urbanpulse

cd "<pasta do repositório>\phase 5 - Kubernetes\MicroServices\location-service"
python seed.py

cd "<pasta do repositório>\phase 5 - Kubernetes\MicroServices\trip-service"
python seed.py

## Iniciar (depois da primeira vez)

Se os pods não estiverem a correr, aplicar os yamls novamente (passo 5).

## Testar os endpoints

**expor o Location Service**

kubectl port-forward svc/location-api 8000:8000 -n urbanpulse

**expor o Analytics Service**

kubectl port-forward svc/analytics-api 8003:8003 -n urbanpulse

**Endpoints:**

http://localhost:8000/health
http://localhost:8000/locations/pickup/ranking
http://localhost:8000/locations/161/profile
http://localhost:8003/health
http://localhost:8003/analytics/mobility-comparison

## Parar

kubectl delete namespace urbanpulse

## Portas

| Serviço           | REST | gRPC  | BD   |
| ----------------- | ---- | ----- | ---- |
| Location Service  | 8000 | 50054 | 5437 |
| Demand Service    | 8002 | 50053 | 5434 |
| Payment Service   | 8006 | 50052 | 5435 |
| Trip Service      | 8001 | 50051 | 5436 |
| Analytics Service | 8003 | —     | —    |
| Revenue Service   | 8007 | 50055 | 5433 |
