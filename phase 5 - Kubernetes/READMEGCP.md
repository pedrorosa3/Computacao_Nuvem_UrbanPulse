# Instruções para correr os meus microservices no GKE do GCP.

## Arquitetura de armazenamento

A base de dados do Location Service corre num pod PostgreSQL no GKE com os dados persistidos num **Google Persistent Disk** através de um **PersistentVolumeClaim (PVC)** de 10GB. Esta configuração é definida no location-db-pvc.yaml

Os ficheiros internos do PostgreSQL estão em `/var/lib/postgresql/data/pgdata` dentro do volume — garantindo que os dados sobrevivem ao reinício dos pods.

## Preparar os ficheiros no Cloud Shell

No Cloud Shell, clicar nos **3 pontos (⋮)** → **Upload** e fazer upload das pastas:

- `location-service/` (sem as pastas `db-data/` e `data/`)
- `analytics-service/`

Depois mover para a pasta correta:

mkdir -p ~/uploadGCP
mv location-service ~/uploadGCP/
mv analytics-service ~/uploadGCP/

### Ficheiros Kubernetes

Fazer upload da pasta `kubernetesCloud/` pelo mesmo método

### CSV do dataset

Fazer upload do ficheiro `yellow_tripdata_2015-01_clean.csv` e do `taxi_zone_lookup.csv`:

mkdir -p ~/uploadGCP/location-service/data
mv yellow_tripdata_2015-01_clean.csv ~/uploadGCP/location-service/data/
mv taxi_zone_lookup.csv ~/uploadGCP/location-service/data/

Nota: O upload só é necessário na primeira vez. O Cloud Shell guarda os ficheiros que fizerem upload.

## 1 - Criar o cluster

gcloud container clusters create urbanpulse \
 --zone=europe-west1-b \
 --num-nodes=2 \
 --machine-type=e2-small \
 --disk-size=20 \
 --no-enable-autoupgrade

Demora mais ou menos 5 minutos.

## 2 -Criar o namespace

kubectl create namespace urbanpulse

## 3 - Criar os ConfigMaps (init.sql de cada DB)

kubectl create configmap location-db-init \
 --from-file=init.sql=/home/diogocsousa27/uploadGCP/location-service/db/init.sql \
 -n urbanpulse

## 4 - Aplicar os yamls

kubectl apply -f ~/kubernetesCloud/location-service/
kubectl apply -f ~/kubernetesCloud/analytics-service/

## 5 - Verificar os pods

Esperar 1 minuto antes de executar o comando, para dar tempo aos pods de iniciarem.

kubectl get pods -n urbanpulse

# todos devem estar: 1/1 Running

## 6. Popular a base de dados (seed)

# Expor a DB

kubectl port-forward svc/location-db 5437:5432 -n urbanpulse &

# Correr o seed

cd ~/uploadGCP/location-service
pip3 install pandas
python3 seed.py

## 7. Verificar o HPA

kubectl get hpa -n urbanpulse

## 8. Testar os endpoints

# Expor os serviços

kubectl port-forward svc/location-api 8000:8000 -n urbanpulse &
kubectl port-forward svc/analytics-api 8003:8003 -n urbanpulse &

Usar o Web Preview no Cloud Shell (ícone no topo) para testar:

/health
/locations/pickup/ranking
/locations/161/profile
/analytics/mobility-comparison

É necessário trocar a porta consoante o microserviço que estamos a verificar.

## 9. Testar rollback

# Ver histórico de versões

kubectl rollout history deployment/location-api -n urbanpulse

# Fazer rollback

kubectl rollout undo deployment/location-api -n urbanpulse

## Como parar para não gastar créditos

gcloud container clusters delete urbanpulse --zone=europe-west1-b

## Portas

| Serviço       | REST | gRPC  | BD   |
| ------------- | ---- | ----- | ---- |
| Location API  | 8000 | 50054 | 5437 |
| Analytics API | 8003 | —     | —    |

## Imagens no Artifact Registry

europe-west1-docker.pkg.dev/fc60250/urbanpulse/location-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/analytics-api:latest
