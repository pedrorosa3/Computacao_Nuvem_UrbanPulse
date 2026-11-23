# Phase 8 — CI/CD com GitHub Actions

## O que foi implementado (60250 — Diogo Sousa)

Foi criado um pipeline de CI/CD com **3 stages** para o **Location Service** e o **Analytics Service**. O pipeline corre automaticamente no GitHub Actions sempre que há alterações ao código, sem precisar de correr nada manualmente.

O ficheiro do pipeline está em `.github/workflows/ci-60250.yml`.

---

## Como funciona o pipeline

O pipeline tem 4 jobs encadeados, activados por 3 triggers distintos:

```
Push para branch 60250  →  Lint + Unit Tests
Pull Request para main  →  Lint + Unit Tests + Pull Request Tests
Push para main          →  Lint + Unit Tests + Integration Tests + Build & Push (CD)
```

---

## Stage 1 — Lint + Unit Tests

**Trigger:** push para o branch individual (`60250`)

**Para que serve:** verificação rápida do dia-a-dia. Corre em segundos e dá feedback imediato durante o desenvolvimento.

**Job 1 — Lint** (corre primeiro, bloqueia os testes se falhar):

- Verifica erros críticos de sintaxe no código do Location e Analytics (variáveis não definidas, imports inválidos, etc.)
- Se encontrar um erro crítico, o pipeline para — os testes não chegam a correr
- Verifica também avisos de estilo mas não bloqueia (só informa)

**Job 2 — Unit Tests** (só corre se o Lint passou):

- Testa funções isoladas, sem base de dados nem serviços externos
- Usa `unittest.mock` para simular as dependências
- Exemplos do que é testado:
  - `_classify_volatility(0.3) == "low"` — função matemática pura
  - `GET /locations/pickup/ranking?start_date=2015-01-31&end_date=2015-01-01` devolve 400 — validação sem BD
  - `GET /locations/pickup/ranking` com BD simulada — verifica que o JSON está correcto

**Ficheiros de testes:** `tests.py` em cada serviço

---

## Stage 2 — Pull Request Tests

**Trigger:** abertura de Pull Request para `main`

**Para que serve:** verificação mais abrangente antes de integrar o código na branch principal. Cobre mais endpoints e cenários de erro do que os unit tests.

**O que diferencia dos Unit Tests:**

- Cobre endpoints que não estão nos unit tests (ex: `/locations/{id}/dropoffs`, `/locations/pairs`)
- Testa cenários de erro mais complexos (ex: o que acontece quando um serviço gRPC está em baixo → deve devolver 503)
- Testa degradação graciosa (ex: Revenue Service falha mas o endpoint continua a responder)
- Continua a usar mocks — não precisa de serviços reais

**Exemplos do que é testado:**

- `classify_zone("Bronx", "Boro Zone") == "peripheral"` — função pura
- `GET /locations/9999/dropoffs` devolve 404 (BD simulada a devolver lista vazia)
- `GET /analytics/mobility-comparison` quando Location gRPC falha → 503
- `GET /analytics/anomalous-trips` quando Revenue falha → continua sem dados de receita

**Ficheiros de testes:** `tests_pr.py` em cada serviço

---

## Stage 3 — Integration Tests

**Trigger:** push para `main` (após merge de PR)

**Para que serve:** verificar que o sistema funciona de verdade com infraestrutura real. Sem mocks — base de dados PostgreSQL real, gRPC real entre serviços.

**Como funciona:**

1. Sobe os 6 microservices + 5 BDs + Redis com Docker Compose (`docker-compose-test.yml`)
2. Aguarda 60 segundos para as BDs iniciarem
3. Corre os seeds de todos os serviços (insere dados de teste reais)
4. Corre os testes contra os serviços reais via HTTP
5. Destrói os containers

**O que verifica:**

- Todos os 6 serviços arrancam correctamente
- Os endpoints do Location Service devolvem dados reais da BD
- O Analytics Service agrega dados reais de todos os outros via gRPC:
  - `demand is not None` → Demand Service respondeu
  - `card_payment_pct is not None` → Payment Service respondeu
  - `avg_fare is not None` → Revenue Service respondeu
  - `revenue_service_used is True` → Revenue respondeu nos anomalous trips
- Comunicação gRPC Location → Demand funciona (`demand_patterns` no zone profile)

**Ficheiros de testes:** `tests_integration/` na raiz da pasta phase 8

**Dados de teste:** `test-data/test_trips.csv` (5000 linhas) e `test-data/taxi_zone_lookup.csv` (265 zonas) — commitados no repositório para o pipeline funcionar sem CSV externo.

---

## CD — Continuous Delivery (Build & Push automático)

**Trigger:** push para `main` — corre **após** os Integration Tests passarem

**Para que serve:** garante que as imagens Docker no Artifact Registry estão sempre actualizadas com o código da branch `main`. Sempre que há um merge, as imagens são construídas automaticamente e enviadas para o registry — sem precisar de correr `gcloud builds submit` manualmente.

**Como funciona:**

1. Autentica no GCP usando uma **Service Account** com permissões mínimas (só escrita no Artifact Registry)
2. Configura o Docker para comunicar com o Artifact Registry
3. Faz `docker build` e `docker push` das 6 imagens para `europe-west1-docker.pkg.dev/fc60250/urbanpulse/`
4. As credenciais GCP são apagadas automaticamente da VM após o job terminar

**Imagens actualizadas automaticamente:**

- `location-api:latest`
- `analytics-api:latest`
- `demand-api:latest`
- `revenue-api:latest`
- `trip-api:latest`
- `payment-service:latest`

**Segurança — o que foi configurado:**

- **Service Account** `github-cd@fc60250.iam.gserviceaccount.com` criada especificamente para este pipeline
- Permissão **apenas** no repositório `urbanpulse` do Artifact Registry (`roles/artifactregistry.writer`) — não tem acesso ao cluster GKE, BDs, nem outros recursos GCP
- As credenciais estão guardadas como **GitHub Secret** (`GCP_SA_KEY`) — nunca aparecem nos logs nem no código
- **Cleanup policy** configurada no Artifact Registry: imagens sem tag com mais de 1 dia são apagadas automaticamente, mantendo o registry limpo

**Nota:** este é **Continuous Delivery**, não Continuous Deployment — o deploy no GKE continua a ser feito manualmente seguindo o `READMECloud.md`. As imagens ficam prontas no registry, mas a decisão de fazer deploy é sempre manual.

---

## CD para o Artifact Registry `computacaonuvem60294` (60294 — Pedro Rosa)

O workflow `.github/workflows/ci-60294.yml` tem um job **Build & Push Images (Artifact Registry 60294)**. Corre em push para `main`, depois dos Integration Tests passarem, e publica as 6 imagens em:

```
europe-west1-docker.pkg.dev/computacaonuvem60294/urbanpulse/<imagem>
```

Cada imagem é publicada com duas tags:
- `:latest`, que é a que os YAMLs de `kubernetesCloud/` usam
- `:<sha curto do commit>`, que serve para rollback

### Se o secret não estiver configurado

O job não falha. Mostra um aviso "CD saltado" e o pipeline fica verde. O mesmo vale para o CD do 60250, que salta quando o secret `GCP_SA_KEY` não existe no repositório. Era esse o erro `must specify exactly one of "workload_identity_provider" or "credentials_json"`.

### Configuração (só uma vez)

> **Pré-requisito:** o projeto `computacaonuvem60294` tem de ter uma **conta de faturação ativa**. Neste momento não tem (a conta de faturação foi fechada), e por isso o `gcloud services enable artifactregistry.googleapis.com` falha com `Billing account ... is not open`. Primeiro liga uma conta ativa com `gcloud billing projects link computacaonuvem60294 --billing-account=<ID_DA_CONTA>` (ver `gcloud billing accounts list`) e ativa os serviços com `gcloud services enable artifactregistry.googleapis.com iam.googleapis.com`.

**1. No Cloud Shell do projeto `computacaonuvem60294`**, criar uma service account só com permissão de escrita no repositório `urbanpulse`:

```bash
gcloud config set project computacaonuvem60294

gcloud artifacts repositories create urbanpulse \
  --repository-format=docker --location=europe-west1   # se ainda não existir

gcloud iam service-accounts create github-cd --display-name="GitHub Actions CD"

gcloud artifacts repositories add-iam-policy-binding urbanpulse \
  --location=europe-west1 \
  --member="serviceAccount:github-cd@computacaonuvem60294.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud iam service-accounts keys create ~/github-cd-key.json \
  --iam-account=github-cd@computacaonuvem60294.iam.gserviceaccount.com
```

**2. No GitHub**, ir a **Settings → Secrets and variables → Actions → New repository secret**:
- Nome: `GCP_SA_KEY_60294`
- Valor: o conteúdo completo de `~/github-cd-key.json` (`cat ~/github-cd-key.json`)

**3. Apagar a chave local** depois de criar o secret:

```bash
rm ~/github-cd-key.json
```

> A chave nunca deve ser commitada. Se a organização GCP bloquear a criação de chaves (`iam.disableServiceAccountKeyCreation`), a alternativa é usar Workload Identity Federation com o input `workload_identity_provider` do `google-github-actions/auth`.

---

## O que precisam fazer

Para adicionar o vosso serviço ao pipeline, são necessárias **4 alterações**:

### 1. Criar `tests.py` no vosso serviço (Unit Tests)

Colocar em `phase 8 - Automation/MicroServices/[vosso-servico]/tests.py`.

O que deve incluir:

- Testes de health (`GET /health` → 200)
- Testes de validação de input (datas inválidas → 400, parâmetros fora do intervalo → 422)
- Testes de funções puras (se existirem)
- Pelo menos um teste com BD simulada usando `unittest.mock.patch`

Exemplo de teste com BD simulada:

```python
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_meu_endpoint():
    mock_dados = [{"id": 1, "valor": 42}]
    with patch("app.routers.meu_router.execute_query", return_value=mock_dados):
        r = client.get("/meu/endpoint")
    assert r.status_code == 200
    assert r.json()[0]["valor"] == 42
```

### 2. Criar `tests_pr.py` no vosso serviço (Pull Request Tests)

Mesma localização. Deve cobrir mais cenários do que o `tests.py`:

- Mais endpoints
- Cenários de erro (404, 503)
- Se o serviço chama outros via gRPC: testar o que acontece quando falham

### 3. Criar testes de integração para o vosso serviço

Os integration tests existem em `tests_integration/` e já testam o location e o analytics. Adicionem testes específicos ao vosso serviço, criem um ficheiro `tests_integration/test_[servico]_integration.py`.

**Regras obrigatórias:**

- **Sem mocks** — o professor confirmou que integration tests com mocks não são integration tests
- Usar `requests.get("http://localhost:PORT/endpoint")` para chamar os serviços reais
- Os serviços são iniciados pelo `docker-compose-test.yml` antes dos testes correrem

Exemplo:

```python
import requests

BASE = "http://localhost:8002"  # porta do vosso serviço

def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200

def test_endpoint_com_dados_reais():
    r = requests.get(f"{BASE}/demand/hourly-matrix")
    assert r.status_code == 200
    data = r.json()
    assert data["overall_avg_trips"] > 0  # verifica que há dados reais
```

O `conftest.py` já aguarda que todos os serviços estejam prontos antes de correr os testes — não é necessário adicionar nada.

### 4. Adicionar o vosso serviço ao workflow

No ficheiro `.github/workflows/ci-NUMERO.yml` (substituir NUMERO pelo número de aluno), adicionar steps para o vosso serviço nos jobs `unit-test` e `pr-test`:

```yaml
- name: Install [Serviço] dependencies
  working-directory: "phase 8 - Automation/MicroServices/[vosso-servico]"
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install pytest pytest-cov httpx

- name: Test [Serviço]
  working-directory: "phase 8 - Automation/MicroServices/[vosso-servico]"
  run: pytest tests.py --junitxml=junit/test-results.xml --cov=app --cov-report=xml
```

---

## Serviços com gRPC no startup (Só para os primeiros 2 stages, nos integration tests NÃO HÁ mocks)

Se o vosso serviço arranca um servidor gRPC no `lifespan` do FastAPI (como o Location Service), é necessário mockar o startup nos testes para evitar erro ao inicializar o TestClient:

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session", autouse=True)
def mock_grpc_server():
    with patch("app.grpc_server.serve_grpc", return_value=MagicMock(stop=MagicMock())):
        yield

@pytest.fixture(scope="session")
def client(mock_grpc_server):
    with TestClient(app) as c:
        yield c
```

---

## Notas importantes

- **Cada aluno deve ter o seu próprio workflow** — o ficheiro deve chamar-se `ci-NUMERO.yml` com o número de aluno, e o trigger deve ser o branch individual
- **Os testes de integração (Stage 3) não usam mocks** — o professor confirmou que integration tests com mocks não são integration tests. O Stage 3 usa serviços Docker reais
- **Os testes de Stage 1 e 2 podem usar mocks** — são unit tests / PR tests, não integration tests
- **Os dados de teste estão em `test-data/`** — o `test_trips.csv` (5000 linhas) e o `taxi_zone_lookup.csv` são usados pelos seeds no Stage 3. O `.gitignore` tem excepções para estes dois ficheiros específicos
- **O seed do Demand precisa de `seed_extra.py`** para popular dados de tendências mensais — correr manualmente depois do `seed.py` se necessário
- **O CD (Build & Push) está implementado** — ao fazer merge para `main`, todas as imagens são actualizadas automaticamente no Artifact Registry. O GitHub Secret `GCP_SA_KEY` tem de estar configurado no repositório para o CD funcionar
