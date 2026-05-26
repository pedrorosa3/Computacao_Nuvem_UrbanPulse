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

## Alertas importantes

- Todos os deployment YAMLs devem apontar para as vossas images no artifact registry.
- Se o seed correr antes do init.sql criar a tabela, o pandas cria-a sem a coluna `id`, o que causa erros no gRPC. Nesse caso, apagar e recriar a tabela manualmente.

## FaaS — Trip Service (primeira vez apenas)

> Para a configuração inicial do FaaS (bucket GCS, permissões, upload do CSV), seguir o **README_FaaS.md** — passos 1 a 5. Só é necessário fazer uma vez.

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
  --num-nodes=5 \
  --machine-type=e2-medium \
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
  --from-file=init.sql=$HOME/MicroServices/location-service/db/init.sql \
  -n urbanpulse

kubectl create configmap demand-db-init \
  --from-file=init.sql=$HOME/MicroServices/demand-service/db/init.sql \
  -n urbanpulse

kubectl create configmap revenue-db-init \
  --from-file=init.sql=$HOME/MicroServices/revenue-service/db/init.sql \
  -n urbanpulse

kubectl create configmap trip-db-init \
  --from-file=init.sql=$HOME/MicroServices/trip-service/db/init.sql \
  -n urbanpulse

kubectl create configmap payment-db-init \
  --from-file=init.sql=$HOME/MicroServices/payment-service/init.sql \
  -n urbanpulse
```

## 4 - Aplicar os Secrets (credenciais das DBs)

> Este passo tem de ser feito ANTES de aplicar os YAMLs dos deployments, para garantir que os pods conseguem ler as credenciais ao arrancar. Se os Secrets não existirem quando os pods iniciarem, ficam em `CreateContainerConfigError`.

```bash
kubectl apply -f ~/kubernetesCloud/location-service/location-secrets.yaml
kubectl apply -f ~/kubernetesCloud/trip-service/trip-secrets.yaml
kubectl apply -f ~/kubernetesCloud/demand-service/demand-secrets.yaml
kubectl apply -f ~/kubernetesCloud/revenue-service/revenue-secrets.yaml
kubectl apply -f ~/kubernetesCloud/payment-service/payment-secrets.yaml
```

## 5 - Aplicar os yamls

> **Atenção:** O Prometheus e Grafana têm de ser aplicados AGORA juntamente com os outros serviços, mesmo que o IP do Ingress ainda não seja conhecido. O Ingress do GCE só atribui IP quando todos os serviços referenciados existem — se o Prometheus ou Grafana não existirem, o Ingress fica bloqueado sem IP indefinidamente.

```bash
kubectl apply -f ~/kubernetesCloud/location-service/
kubectl apply -f ~/kubernetesCloud/analytics-service/
kubectl apply -f ~/kubernetesCloud/demand-service/
kubectl apply -f ~/kubernetesCloud/revenue-service/
kubectl apply -f ~/kubernetesCloud/trip-service/
kubectl apply -f ~/kubernetesCloud/payment-service/
kubectl apply -f ~/kubernetesCloud/redis.yaml
kubectl apply -f ~/kubernetesCloud/prometheus.yaml
kubectl apply -f ~/kubernetesCloud/grafana.yaml

# Verificar que todos os serviços existem antes de aplicar o Ingress
kubectl get svc -n urbanpulse
# Devem aparecer 14 serviços incluindo prometheus e grafana

kubectl apply -f ~/kubernetesCloud/ingress.yaml
```

## 6 - Verificar os pods (aguardar 1-2 minutos)

Esperar 1-2 minutos antes de executar o comando, para dar tempo aos pods de iniciarem.

```bash
kubectl get pods -n urbanpulse
# todos devem estar: 1/1 Running
```

## 7 - Popular a base de dados (seed)

> Correr o seed DEPOIS dos pods estarem todos 1/1 Running, para garantir que as tabelas já foram criadas pelo init.sql.
> **Nota:** O Trip Service não tem seed manual — os dados são inseridos automaticamente pela Cloud Function (ver passos FaaS abaixo).

```bash
# Location
kubectl port-forward svc/location-db 5437:5432 -n urbanpulse &
sleep 2
cd ~/MicroServices/location-service
pip3 install pandas sqlalchemy psycopg2-binary
python3 seed.py

# Demand
kubectl port-forward svc/demand-db 5434:5432 -n urbanpulse &
sleep 2
cd ~/MicroServices/demand-service
pip3 install pandas sqlalchemy psycopg2-binary
python3 seed.py

# Revenue
kubectl port-forward svc/revenue-db 5433:5432 -n urbanpulse &
sleep 2
cd ~/MicroServices/revenue-service
pip3 install pandas sqlalchemy psycopg2-binary
python3 seed.py

# Payment
kubectl port-forward svc/payment-db 5435:5432 -n urbanpulse &
sleep 2
cd ~/MicroServices/payment-service
pip3 install pandas sqlalchemy psycopg2-binary
python3 seed.py
```

## 8 - Verificar o HPA / Ingress / Redis

```bash
kubectl get hpa -n urbanpulse

kubectl get ingress -n urbanpulse

kubectl exec -it deploy/redis -n urbanpulse -- redis-cli ping
```

Aguardar que o Ingress tenha um IP atribuído na coluna `ADDRESS`. Guardar esse IP — é necessário nos passos seguintes. Este IP pode demorar vários minutos a aparecer.

## 9 - Actualizar o IP no Prometheus e Grafana

> O Prometheus e o Grafana já foram aplicados no passo 5. Agora que o Ingress tem IP, é necessário actualizar esse IP nos ficheiros e reaplicar — caso contrário o Prometheus e o Grafana não funcionam correctamente.

Atualizar o IP nos dois ficheiros:

```yaml
# Em prometheus.yaml, dentro do Deployment:
args:
  - "--web.external-url=http://<IP_DO_INGRESS>/prometheus" # <- atualizar aqui
  - "--web.route-prefix=/prometheus"
```

```yaml
# Em grafana.yaml, dentro do Deployment:
env:
  - name: GF_SERVER_ROOT_URL
    value: "http://<IP_DO_INGRESS>/grafana" # <- atualizar aqui
```

Reaplicar os dois ficheiros:

```bash
kubectl apply -f ~/kubernetesCloud/prometheus.yaml
kubectl apply -f ~/kubernetesCloud/grafana.yaml
```

Confirmar que os pods arrancaram:

```bash
kubectl get pods -n urbanpulse | grep -E "prometheus|grafana"
# ambos devem estar: 1/1 Running
```

O GCE Load Balancer demora 3-5 minutos a propagar os novos backends. Após esse tempo, aceder a:

- Prometheus: `http://<IP>/prometheus` → **Status → Targets** — os três targets (`location-api`, `analytics-api`, `payment-service`) devem aparecer como `UP`
- Grafana: `http://<IP>/grafana` — credenciais: utilizador `admin`, password `urbanpulse2026`

## 10 - Configurar o Grafana

A datasource do Prometheus já está configurada automaticamente. Para verificar:

**Connections → Data sources → Prometheus → Save & test**

Deve aparecer: _"Successfully queried the Prometheus API."_

Para criar um dashboard: **Dashboards → New → New dashboard → Add visualization → selecionar Prometheus como datasource**.

> **Nota:** Os dashboards criados manualmente no Grafana perdem-se quando o cluster é apagado.

## 11 - FaaS — Popular a Trip DB

> Estes passos substituem o `seed.py` do Trip Service. A Cloud Function insere os dados automaticamente quando acionada.

**11.1 — Expor a Trip DB como LoadBalancer**

A Cloud Function corre fora do cluster GKE e não consegue aceder ao `ClusterIP`. É necessário expô-la temporariamente:

```bash
nano ~/kubernetesCloud/trip-service/trip-db-service.yaml
# Mudar: type: ClusterIP → type: LoadBalancer

kubectl apply -f ~/kubernetesCloud/trip-service/trip-db-service.yaml
```

Esperar 1-2 minutos e obter o IP externo:

```bash
kubectl get svc trip-db -n urbanpulse
```

Copiar o valor da coluna `EXTERNAL-IP`.

**11.2 — Deploy da Cloud Function**

```bash
gcloud functions deploy trip-data-ingestion \
  --gen2 \
  --runtime=python311 \
  --region=europe-west1 \
  --source=/home/$USER/CloudFunction \
  --entry-point=ingest_trips \
  --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
  --trigger-event-filters="bucket=urbanpulse-trip-data" \
  --set-env-vars DB_HOST=EXTERNAL_IP_DA_TRIP_DB,DB_PORT=5432,DB_NAME=trip_db,DB_USER=admin,DB_PASSWORD=isqueiro20 \
  --memory=4Gi \
  --timeout=540s
```

Substituir `EXTERNAL_IP_DA_TRIP_DB` pelo IP obtido acima.

**11.3 — Acionar a função**

```bash
gcloud storage cp gs://urbanpulse-trip-data/yellow_tripdata_2015-01_clean.csv gs://urbanpulse-trip-data/trigger.csv
```

**11.4 — Acompanhar os logs**

```bash
gcloud functions logs read trip-data-ingestion --region=europe-west1 --gen2 --limit=20
```

**11.5 — Confirmar dados na DB**

```bash
kubectl port-forward svc/trip-db 5436:5432 -n urbanpulse &
sleep 2
psql -h localhost -p 5436 -U admin -d trip_db -c "SELECT COUNT(*) FROM trips;"
```

## 12 - Expor os serviços

```bash
kubectl port-forward svc/location-api 8000:8000 -n urbanpulse &
kubectl port-forward svc/trip-api 8001:8001 -n urbanpulse &
kubectl port-forward svc/demand-api 8002:8002 -n urbanpulse &
kubectl port-forward svc/analytics-api 8003:8003 -n urbanpulse &
kubectl port-forward svc/payment-svc 8006:8006 -n urbanpulse &
kubectl port-forward svc/revenue-api 8007:8007 -n urbanpulse &
```

## 13 - Testar os endpoints

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

Depois de testar alguns endpoints onde o Redis foi implementado verificar o resultado do seguinte comando:

```
kubectl exec -it deploy/redis -n urbanpulse -- redis-cli KEYS '*'
```

Apenas deve de contar quando são chamados endpoints que estão definidos a usar cache do redis.

## 14 - Testar rollback

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
gcloud functions delete trip-data-ingestion --region=europe-west1 --gen2
gcloud container clusters delete urbanpulse --zone=europe-west1-b
```

Verificar também em **Compute Engine → Disks** se ficaram discos órfãos e apagá-los.

## Portas

| Serviço           | REST | gRPC  | BD (port-forward) |
| ----------------- | ---- | ----- | ----------------- |
| Location Service  | 8000 | 50054 | 5437              |
| Demand Service    | 8002 | 50053 | 5434              |
| Payment Service   | 8006 | 50052 | 5435              |
| Trip Service      | 8001 | 50051 | 5436              |
| Analytics Service | 8003 | —     | —                 |
| Revenue Service   | 8007 | 50055 | 5433              |
| Prometheus        | 9090 | —     | —                 |
| Grafana           | 3000 | —     | —                 |
| Redis             | 6379 | —     | —                 |

## Imagens no Artifact Registry

```
europe-west1-docker.pkg.dev/fc60250/urbanpulse/location-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/analytics-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/demand-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/revenue-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/trip-api:latest
europe-west1-docker.pkg.dev/fc60250/urbanpulse/payment-service:latest
```
