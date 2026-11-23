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
- `.env` (criado a partir do `.env.example`, com as passwords)

> Nota: O upload só é necessário na primeira vez. O Cloud Shell guarda os ficheiros entre sessões.

## Alertas importantes

- Todos os deployment YAMLs devem apontar para as vossas images no artifact registry.
- Se o seed correr antes do init.sql criar a tabela, o pandas cria-a sem a coluna `id`, o que causa erros no gRPC. Nesse caso, apagar e recriar a tabela manualmente.

## 0 - Criar o Artifact Registry e fazer push das imagens (Mudar o fc60250 para o nome do vosso projeto)

```bash
gcloud artifacts repositories create urbanpulse \
  --repository-format=docker \
  --location=europe-west1

cd ~/MicroServices/location-service
gcloud builds submit --tag europe-west1-docker.pkg.dev/fc60250/urbanpulse/location-api:latest .

cd ~/MicroServices/analytics-service
gcloud builds submit --tag europe-west1-docker.pkg.dev/fc60250/urbanpulse/analytics-api:latest .

cd ~/MicroServices/demand-service
gcloud builds submit --tag europe-west1-docker.pkg.dev/fc60250/urbanpulse/demand-api:latest .

cd ~/MicroServices/revenue-service
gcloud builds submit --tag europe-west1-docker.pkg.dev/fc60250/urbanpulse/revenue-api:latest .

cd ~/MicroServices/trip-service
gcloud builds submit --tag europe-west1-docker.pkg.dev/fc60250/urbanpulse/trip-api:latest .

cd ~/MicroServices/payment-service
gcloud builds submit --tag europe-west1-docker.pkg.dev/fc60250/urbanpulse/payment-service:latest .
```

Verificar que as 6 imagens estão no registry:

```bash
gcloud artifacts docker images list europe-west1-docker.pkg.dev/fc60250/urbanpulse
```

## 1 - Criar o cluster

```bash
gcloud container clusters create urbanpulse \
  --zone=europe-west1-b \
  --num-nodes=4 \
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

> Este passo tem de ser feito ANTES de aplicar os YAMLs, para garantir que o PostgreSQL cria as tabelas com o schema correto.

```bash
kubectl create configmap location-db-init \
  --from-file=init.sql=/home/diogocsousa27/MicroServices/location-service/db/init.sql \
  -n urbanpulse

kubectl create configmap demand-db-init \
  --from-file=init.sql=/home/diogocsousa27/MicroServices/demand-service/db/init.sql \
  -n urbanpulse

kubectl create configmap revenue-db-init \
  --from-file=init.sql=/home/diogocsousa27/MicroServices/revenue-service/db/init.sql \
  -n urbanpulse

kubectl create configmap trip-db-init \
  --from-file=init.sql=/home/diogocsousa27/MicroServices/trip-service/db/init.sql \
  -n urbanpulse

kubectl create configmap payment-db-init \
  --from-file=init.sql=/home/diogocsousa27/MicroServices/payment-service/init.sql \
  -n urbanpulse
```

## 3.1 - Criar os Secrets (passwords das DBs)

As passwords já não estão nos YAMLs. Estão no ficheiro `.env`, que não vai para o Git. Fazer upload do `.env` para a home do Cloud Shell (`~/.env`), criado a partir do `.env.example`, e correr:

```bash
bash ~/kubernetesCloud/create-secrets.sh
```

> Este passo tem de ser feito ANTES de aplicar os YAMLs. Sem os Secrets, os pods ficam em `CreateContainerConfigError`.

## 4 - Aplicar os yamls

```bash
kubectl apply -f ~/kubernetesCloud/location-service/
kubectl apply -f ~/kubernetesCloud/analytics-service/
kubectl apply -f ~/kubernetesCloud/demand-service/
kubectl apply -f ~/kubernetesCloud/revenue-service/
kubectl apply -f ~/kubernetesCloud/trip-service/
kubectl apply -f ~/kubernetesCloud/payment-service/
kubectl apply -f ~/kubernetesCloud/ingress.yaml
```

## 5 - Verificar os pods

Esperar 1-2 minutos antes de executar o comando, para dar tempo aos pods de iniciarem.

```bash
kubectl get pods -n urbanpulse
# todos devem estar: 1/1 Running
```

## 6 - Popular a base de dados (seed)

> Correr o seed DEPOIS dos pods estarem todos 1/1 Running, para garantir que as tabelas já foram criadas pelo init.sql.

```bash
# Location
kubectl port-forward svc/location-db 5437:5432 -n urbanpulse &
sleep 2
cd ~/MicroServices/location-service
pip3 install pandas
python3 seed.py

# Demand
kubectl port-forward svc/demand-db 5434:5432 -n urbanpulse &
sleep 2
cd ~/MicroServices/demand-service
python3 seed.py

# Revenue
kubectl port-forward svc/revenue-db 5433:5432 -n urbanpulse &
sleep 2
cd ~/MicroServices/revenue-service
python3 seed.py

# Trip
kubectl port-forward svc/trip-db 5436:5432 -n urbanpulse &
sleep 2
cd ~/MicroServices/trip-service
python3 seed.py

# Payment
kubectl port-forward svc/payment-db 5435:5432 -n urbanpulse &
sleep 2
cd ~/MicroServices/payment-service
pip install sqlalchemy psycopg2-binary
python3 seed.py
```

## 7 - Verificar o HPA / Ingress

```bash
kubectl get hpa -n urbanpulse

kubectl get ingress -n urbanpulse
```


## 8 - Expor os serviços

```bash
kubectl port-forward svc/location-api 8000:8000 -n urbanpulse &
kubectl port-forward svc/trip-api 8001:8001 -n urbanpulse &
kubectl port-forward svc/demand-api 8002:8002 -n urbanpulse &
kubectl port-forward svc/analytics-api 8003:8003 -n urbanpulse &
kubectl port-forward svc/payment-svc 8006:8006 -n urbanpulse &
kubectl port-forward svc/revenue-api 8007:8007 -n urbanpulse &
```

## 9 - Testar os endpoints

Usar o Web Preview no Cloud Shell (ícone no topo) para testar. O `?authuser=2` deve estar sempre no fim do URL.

```
https://8000-cs-XXXXXXX-default.cs-europe-west1-haha.cloudshell.dev/locations/pickup/ranking?authuser=2
https://8000-cs-XXXXXXX-default.cs-europe-west1-haha.cloudshell.dev/locations/161/profile?authuser=2
https://8003-cs-XXXXXXX-default.cs-europe-west1-haha.cloudshell.dev/analytics/mobility-comparison?authuser=2
https://8006-cs-XXXXXXX-default.cs-europe-west1-haha.cloudshell.dev/docs?authuser=2
https://8002-cs-XXXXXXX-default.cs-europe-west1-haha.cloudshell.dev/docs?authuser=2
https://8007-cs-XXXXXXX-default.cs-europe-west1-haha.cloudshell.dev/docs?authuser=2
https://8001-cs-XXXXXXX-default.cs-europe-west1-haha.cloudshell.dev/docs?authuser=2
```

> Substituir `XXXXXXX` pelo ID do vosso Cloud Shell (ex: `146652400283`). Este ID é encontrado se abrirem uma web preview.

## 10 - Testar rollback

```bash
# Ver histórico de versões
kubectl rollout history deployment/location-api -n urbanpulse
kubectl rollout history deployment/payment-deploy -n urbanpulse

# Fazer rollback
kubectl rollout undo deployment/location-api -n urbanpulse
kubectl rollout undo deployment/payment-deploy -n urbanpulse
```

## Como parar para não gastar créditos

```bash
gcloud container clusters delete urbanpulse --zone=europe-west1-b
```

Verificar também em **Compute Engine → Disks** se ficaram discos órfãos e apagá-los.

## Portas

| Serviço           | REST | gRPC  | BD (port-forward ) |
| ----------------- | ---- | ----- | ------------------ |
| Location Service  | 8000 | 50054 | 5437               |
| Demand Service    | 8002 | 50053 | 5434               |
| Payment Service   | 8006 | 50052 | 5435               |
| Trip Service      | 8001 | 50051 | 5436               |
| Analytics Service | 8003 | —     | —                  |
| Revenue Service   | 8007 | 50055 | 5433               |

## Imagens no Artifact Registry

```
europe-west1-docker.pkg.dev/fc60250/urbanpulse/location-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/analytics-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/demand-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/revenue-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/trip-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/payment-service:latest
```
