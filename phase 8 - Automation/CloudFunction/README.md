# Phase 7 — FaaS: Serverless Trip Data Ingestion

## O que faz

Uma **Google Cloud Function** acionada automaticamente quando um ficheiro CSV é carregado para um bucket do Google Cloud Storage. A função processa o CSV em chunks, calcula as colunas enriquecidas e insere os dados na Trip DB — substituindo o processo manual do `seed.py`.

## Resultado esperado

Após o upload do CSV para o bucket, a função insere automaticamente os dados na Trip DB. O endpoint `/trips/classification/time-of-day` deve devolver dados com `total_trips` igual ao número de viagens no CSV.

---

## Passos (só na primeira vez)

### 1 — Habilitar os serviços necessários

```bash
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable eventarc.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
```

### 2 — Criar o bucket GCS

```bash
gcloud storage buckets create gs://urbanpulse-trip-data \
  --location=europe-west1 \
  --project=SEU_PROJECT_ID
```

Substituir `SEU_PROJECT_ID` pelo vosso project ID (ex: `fcul60264`).

### 3 — Dar permissões ao Eventarc e Cloud Storage

```bash
PROJECT_NUMBER=$(gcloud projects describe SEU_PROJECT_ID --format="value(projectNumber)")

gcloud projects add-iam-policy-binding SEU_PROJECT_ID \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-eventarc.iam.gserviceaccount.com" \
  --role="roles/eventarc.eventReceiver"

gcloud projects add-iam-policy-binding SEU_PROJECT_ID \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gs-project-accounts.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"

gsutil iam ch \
  serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-eventarc.iam.gserviceaccount.com:roles/storage.objectViewer \
  gs://urbanpulse-trip-data
```

### 4 — Fazer upload da pasta CloudFunction

No Cloud Shell, clicar nos **3 pontos (⋮) → Upload** e fazer upload da pasta `CloudFunction/`.

### 5 — Fazer upload do CSV para o bucket (só uma vez)

```bash
# Desativar o upload paralelo para evitar que a função seja acionada por chunks
gcloud config set storage/parallel_composite_upload_enabled False

gcloud storage cp ~/yellow_tripdata_2015-01_clean.csv gs://urbanpulse-trip-data/
```

> **Nota:** O CSV fica no bucket permanentemente. Não é necessário fazer upload novamente nas sessões seguintes.

---

## Passos (cada vez que o cluster é recriado)

### 6 — Subir o cluster e aplicar os YAMLs

Seguir o `READMECloud.md` até ao passo 5 (pods a correr). **Não correr o seed.py do trip-service** — a Cloud Function trata disso.

### 7 — Expor a Trip DB externamente (necessário para a Cloud Function aceder)

A Cloud Function corre fora do cluster GKE, por isso o `ClusterIP` não é acessível. É necessário expor a Trip DB com um `LoadBalancer` temporariamente:

```bash
# Editar o service da trip-db
nano ~/kubernetesCloud/trip-service/trip-db-service.yaml
# Mudar: type: ClusterIP → type: LoadBalancer

kubectl apply -f ~/kubernetesCloud/trip-service/trip-db-service.yaml
```

Esperar 1-2 minutos e obter o IP externo:

```bash
kubectl get svc trip-db -n urbanpulse
```

Copiar o valor da coluna `EXTERNAL-IP`.

### 8 — Deploy da Cloud Function

```bash
set -a; source ~/.env; set +a   # carrega TRIP_DB_PASSWORD

gcloud functions deploy trip-data-ingestion \
  --gen2 \
  --runtime=python311 \
  --region=europe-west1 \
  --source=/home/$USER/CloudFunction \
  --entry-point=ingest_trips \
  --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
  --trigger-event-filters="bucket=urbanpulse-trip-data" \
  --set-env-vars DB_HOST=EXTERNAL_IP_DA_TRIP_DB,DB_PORT=5432,DB_NAME=trip_db,DB_USER=admin,DB_PASSWORD="$TRIP_DB_PASSWORD" \
  --memory=4Gi \
  --timeout=540s
```

Substituir `EXTERNAL_IP_DA_TRIP_DB` pelo IP obtido no passo 7.

Demora ~3 minutos. Quando terminar deves ver `State: ACTIVE`.

### 9 — Acionar a função

O CSV já está no bucket do passo 5. Para acionar a função sem fazer novo upload:

```bash
# Fazer uma cópia dentro do bucket — aciona o trigger automaticamente
gcloud storage cp gs://urbanpulse-trip-data/yellow_tripdata_2015-01_clean.csv gs://urbanpulse-trip-data/trigger.csv
```

> **Nota:** Não apagar o `trigger.csv` antes da função terminar de processar.

### 10 — Acompanhar os logs

```bash
gcloud functions logs read trip-data-ingestion --region=europe-west1 --gen2 --limit=20
```

Deves ver:
```
Triggered by file: trigger.csv
Downloading CSV from GCS...
Download complete
Connected and truncated table
Processing CSV in chunks of 50000 rows...
Inserted 50000 rows so far...
Inserted 100000 rows so far...
...
SUCCESS: X trips inserted from file trigger.csv
```

A função demora ~10-15 minutos para o CSV completo (~12M viagens).

### 11 — Confirmar dados na DB

```bash
kubectl port-forward svc/trip-db 5436:5432 -n urbanpulse &
sleep 2
psql -h localhost -p 5436 -U admin -d trip_db -c "SELECT COUNT(*) FROM trips;"
```

### 12 — Testar o endpoint

Via Ingress (obter o IP com `kubectl get ingress -n urbanpulse`):
```
http://IP_DO_INGRESS/trips/classification/time-of-day
http://IP_DO_INGRESS/trips/health
```

---

## Parar para não gastar créditos

```bash
# Apagar a função
gcloud functions delete trip-data-ingestion --region=europe-west1 --gen2

# Apagar o cluster
gcloud container clusters delete urbanpulse --zone=europe-west1-b

# Verificar discos órfãos e apagar
gcloud compute disks list
```



