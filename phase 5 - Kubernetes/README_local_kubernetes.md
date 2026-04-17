# Kubernetes Local — Demand Service & Revenue Service

## Pré-requisitos
- Docker Desktop com Kubernetes ativado (ou minikube)
- kubectl configurado
- Imagens dos microserviços construídas localmente

---

## 1. Ir para a pasta do projeto

```bash
cd "C:\Users\Francisco\Desktop\Cloud-Computing\phase 4 - Implementation"
```

---

## 2. Criar o namespace (só uma vez)

```bash
kubectl create namespace urbanpulse
```

---

## 3. Criar os ConfigMaps com os init.sql

### Demand Service
```bash
kubectl create configmap demand-db-init \
  --from-file=init.sql=./demand-service/db/init.sql \
  -n urbanpulse
```

### Revenue Service
```bash
kubectl create configmap revenue-db-init \
  --from-file=init.sql=./revenue-service/db/init.sql \
  -n urbanpulse
```

> **Nota:** Verifica o caminho exato do init.sql dentro de cada serviço. Pode ser `db/init.sql` ou diretamente `init.sql` na raiz do serviço.

---

## 4. Build das imagens

```bash
docker build -t demand-api:latest ./demand-service
docker build -t revenue-api:latest ./revenue-service
```

---

## 5. Aplicar os YAMLs

### Demand Service
```bash
kubectl apply -f "../phase 5 - Kubernetes/kubernetes/demand-service/"
```

### Revenue Service
```bash
kubectl apply -f "../phase 5 - Kubernetes/kubernetes/revenue-service/"
```

---

## 6. Verificar que os pods estão a correr

```bash
kubectl get pods -n urbanpulse
```

Esperar até todos estarem `1/1 Running`. Pode demorar 1-2 minutos.

---

## 7. Popular as bases de dados (seed)

### Demand Service

**Expor a BD:**
```bash
kubectl port-forward svc/demand-db 5434:5432 -n urbanpulse
```

**Noutro terminal, correr o seed:**
```bash
cd ./demand-service
python seed.py
python seed_extra.py
```

### Revenue Service

**Expor a BD:**
```bash
kubectl port-forward svc/revenue-db 5433:5432 -n urbanpulse
```

**Noutro terminal, correr o seed:**
```bash
cd ./revenue-service
python seed.py
```

---

## 8. Testar os endpoints

**Expor o Demand Service:**
```bash
kubectl port-forward svc/demand-api 8002:8002 -n urbanpulse
```

**Expor o Revenue Service:**
```bash
kubectl port-forward svc/revenue-api 8007:8007 -n urbanpulse
```

**Endpoints de teste:**

```
http://localhost:8002/health
http://localhost:8002/demand/hourly-matrix?year=2015
http://localhost:8002/demand/monthly-trend?year_from=2015
http://localhost:8002/demand/zone-volatility?zone_id=161

http://localhost:8007/health
http://localhost:8007/revenue/avg-fare-by-zone
http://localhost:8007/revenue/breakdown
http://localhost:8007/revenue/fare-per-km
```

---

## 9. Testar rollback

```bash
# Ver histórico
kubectl rollout history deployment/demand-api -n urbanpulse
kubectl rollout history deployment/revenue-api -n urbanpulse

# Fazer rollback
kubectl rollout undo deployment/demand-api -n urbanpulse
kubectl rollout undo deployment/revenue-api -n urbanpulse
```

---

## Parar tudo

```bash
kubectl delete namespace urbanpulse
```

---

## Portas

| Serviço      | REST | gRPC  | BD   |
| ------------ | ---- | ----- | ---- |
| Demand API   | 8002 | 50053 | 5434 |
| Revenue API  | 8007 | 50055 | 5433 |
