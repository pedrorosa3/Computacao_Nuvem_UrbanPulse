# Instruções para correr os meus microservices no GKE do GCP.

## Arquitetura de armazenamento

A base de dados do Location Service corre num pod PostgreSQL no GKE com os dados persistidos num **Google Persistent Disk** através de um **PersistentVolumeClaim (PVC)** de 10GB. Esta configuração é definida no location-db-pvc.yaml

Os ficheiros internos do PostgreSQL estão em `/var/lib/postgresql/data/pgdata` dentro do volume — garantindo que os dados sobrevivem ao reinício dos pods.

## Trocar o caminho dos diversos seed.py

Como o CSV é partilhado por todos os microservices, todos os seed.py devem apontar para o diretório home do Cloud Shell, no meu caso:
`/home/diogocsousa27/yellow_tripdata_2015-01_clean.csv`

## Preparar os ficheiros no Cloud Shell

No Cloud Shell, clicar nos **3 pontos (⋮)** → **Upload** e fazer upload das pastas:

- `MicroServices`
- `kubernetesCloud`

E dos ficheiros CSV:

- `yellow_tripdata_2015-01_clean.csv`
- `taxi_zone_lookup.csv`

> Nota: O upload só é necessário na primeira vez. O Cloud Shell guarda os ficheiros entre sessões.

## 1 - Criar o cluster

```bash
gcloud container clusters create urbanpulse \
  --zone=europe-west1-b \
  --num-nodes=2 \
  --machine-type=e2-small \
  --disk-size=20 \
  --no-enable-autoupgrade
```

Demora mais ou menos 5 minutos.

## 2 - Criar o namespace

```bash
kubectl create namespace urbanpulse
```

## 3 - Criar os ConfigMaps (init.sql de cada DB)

```bash
kubectl create configmap location-db-init \
  --from-file=init.sql=/home/diogocsousa27/MicroServices/location-service/db/init.sql \
  -n urbanpulse
```

## 4 - Aplicar os yamls

```bash
kubectl apply -f ~/kubernetesCloud/location-service/
kubectl apply -f ~/kubernetesCloud/analytics-service/
```

## 5 - Verificar os pods

Esperar 1 minuto antes de executar o comando, para dar tempo aos pods de iniciarem.

```bash
kubectl get pods -n urbanpulse
# todos devem estar: 1/1 Running
```

## 6 - Popular a base de dados (seed)

```bash
# Expor a DB
kubectl port-forward svc/location-db 5437:5432 -n urbanpulse &

# Correr o seed
cd ~/MicroServices/location-service
pip3 install pandas
python3 seed.py
```

## 7 - Verificar o HPA

```bash
kubectl get hpa -n urbanpulse
```

## 8 - Testar os endpoints

```bash
kubectl port-forward svc/location-api 8000:8000 -n urbanpulse &
kubectl port-forward svc/analytics-api 8003:8003 -n urbanpulse &
```

Usar o Web Preview no Cloud Shell (ícone no topo) para testar:

- `/health`
- `/locations/pickup/ranking`
- `/locations/161/profile`
- `/analytics/mobility-comparison`

> É necessário trocar a porta consoante o microserviço que estamos a verificar.

## 9 - Testar rollback

```bash
# Ver histórico de versões
kubectl rollout history deployment/location-api -n urbanpulse

# Fazer rollback
kubectl rollout undo deployment/location-api -n urbanpulse
```

## Como parar para não gastar créditos

```bash
gcloud container clusters delete urbanpulse --zone=europe-west1-b
```

## Portas

| Serviço       | REST | gRPC  | BD   |
| ------------- | ---- | ----- | ---- |
| Location API  | 8000 | 50054 | 5437 |
| Analytics API | 8003 | —     | —    |

## Imagens no Artifact Registry

```
europe-west1-docker.pkg.dev/fc60250/urbanpulse/location-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/analytics-api:latest
```
