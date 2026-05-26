Indicações para correr o kubernetes localmente

### 1. Ir para a pasta do projeto

cd "C:\Users\Diogo Sousa\Desktop\FCUL\Mestrado\CN\Cloud-Computing\phase 4 - Implementation"

### 2. Criar o namespace

kubectl create namespace urbanpulse

### 3. Criar o ConfigMap do init.sql do Location Service

kubectl create configmap location-db-init `  --from-file=init.sql=./location-service/db/init.sql` -n urbanpulse

### 4. Build das imagens necessárias

docker build -t location-api:latest ./location-service
docker build -t analytics-api:latest ./analytics-service

### 5. Aplicar os yamls

kubectl apply -f "../phase 5 - Kubernetes/kubernetes/location-service/"
kubectl apply -f "../phase 5 - Kubernetes/kubernetes/analytics-service/"

### 6. Verificar que os pods estão a correr

kubectl get pods -n urbanpulse

### 7. Popular a base de dados (seed)

**Expor a BD**
kubectl port-forward svc/location-db 5437:5432 -n urbanpulse

cd "C:\Users\Diogo Sousa\Desktop\FCUL\Mestrado\CN\Cloud-Computing\phase 4 - Implementation\location-service"

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
