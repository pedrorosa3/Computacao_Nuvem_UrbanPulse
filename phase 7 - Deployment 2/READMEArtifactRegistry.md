# Como fazer push de uma imagem para o Artifact Registry

## 1 — Abrir o Cloud Shell

Aceder a https://console.cloud.google.com e clicar no ícone `>_` no canto superior direito.

---

## 2 — Build e push da imagem
Criar repo para as imagens, caso nao esteja já criado
```bash
gcloud artifacts repositories create urbanpulse \
  --repository-format=docker \
  --location=europe-west1 \
  --description="Repo de imagens"
```

```bash
cd ~/MicroServices/[nome-servico]
gcloud builds submit --tag europe-west1-docker.pkg.dev/fc60250/urbanpulse/[nome-servico]:latest .
```

Demora ~2-3 minutos. Quando terminar deves ver `STATUS: SUCCESS`.

---

## Exemplos por serviço

| Serviço         | Comando                                                                                              |
| --------------- | ---------------------------------------------------------------------------------------------------- |
| demand-service  | `gcloud builds submit --tag europe-west1-docker.pkg.dev/fc60250/urbanpulse/demand-api:latest .`  |
| payment-service | `gcloud builds submit --tag europe-west1-docker.pkg.dev/fc60250/urbanpulse/payment-api:latest .` |
| trip-service    | `gcloud builds submit --tag europe-west1-docker.pkg.dev/fc60250/urbanpulse/trip-api:latest .`    |
| revenue-service | `gcloud builds submit --tag europe-west1-docker.pkg.dev/fc60250/urbanpulse/revenue-api:latest .` |

---

## Verificar que a imagem foi guardada

```bash
gcloud artifacts docker images list europe-west1-docker.pkg.dev/fc60250/urbanpulse
```

---

## Notas

- O repositório `urbanpulse` já está criado no Artifact Registry — não é necessário criar um novo.
- O Cloud Build já tem permissões configuradas — não é necessário fazer nenhuma configuração adicional.
- Só é necessário fazer push quando o código muda. Se o código não mudou, a imagem já está no Artifact Registry.
