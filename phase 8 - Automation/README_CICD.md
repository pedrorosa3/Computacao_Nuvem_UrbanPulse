# Phase 8 — CI/CD com GitHub Actions

## Objetivo da fase

Criar um pipeline de CI/CD que corra automaticamente quando há alterações ao código, garantindo que o código está correto antes de ser integrado na branch principal. O pipeline deve demonstrar a aplicação de **vários tipos de testes em diferentes fases** do desenvolvimento.

O professor vai prestar atenção à qualidade e variedade dos testes — não é necessário cobertura total, mas os testes têm de ser reais e demonstrar que percebem o que estão a testar.

---

## Estrutura do pipeline — 3 stages

O pipeline tem 3 momentos distintos, cada um com um trigger e um propósito diferente:

```
Push para branch individual  →  Stage 1 (lint + unit tests)
Pull Request para main        →  Stage 2 (staging tests)
Push para main                →  Stage 3 (integration tests + build imagem)
```

---

## Stage 1 — Unit Tests

**Trigger:** push para o vosso branch individual (ex: `60250`, `60252`, etc.)

**Propósito:** verificar rapidamente que o código está correto antes de partilhar com o grupo. Corre em cada push do dia-a-dia.

**O que deve conter:**

**Job 1 — Lint** (corre primeiro, bloqueia os testes se falhar):
- Instalar `flake8`
- Correr com `--select=E9,F63,F7,F82` — só erros críticos de sintaxe que impedem o código de correr
- Correr com `--exit-zero --max-line-length=127` — avisos de estilo, não bloqueia

**Job 2 — Unit Tests** (só corre se o lint passou):
- Instalar dependências do serviço + `pytest`, `pytest-cov`, `httpx`
- Correr `pytest tests.py --cov=app`

**Tipos de testes a incluir no `tests.py`:**
- **Health** — verificar que `/health` devolve 200 e `{"status": "ok"}`
- **Validação de input** — parâmetros inválidos devolvem 400 ou 422 (sem precisar de BD)
- **Lógica pura** — testar directamente funções Python que não dependem de nada externo (ex: funções de classificação, cálculos matemáticos)
- **Endpoint com BD simulada** — usar `unittest.mock.patch` para substituir as chamadas à BD por dados fictícios e verificar que o endpoint formata bem a resposta

**Exemplo de teste com BD simulada:**
```python
from unittest.mock import patch

def test_meu_endpoint(client):
    mock_dados = [{"id": 1, "nome": "Exemplo"}]
    with patch("app.routers.meu_router.execute_query", return_value=mock_dados):
        r = client.get("/meu/endpoint")
    assert r.status_code == 200
    assert r.json()[0]["nome"] == "Exemplo"
```

---

## Stage 2 — Staging Tests

**Trigger:** Pull Request para `main`

**Propósito:** nível de qualidade mais exigente antes de integrar na branch principal. Testa como os componentes trabalham em conjunto e como o sistema se comporta quando algo corre mal.

**Configuração no workflow:**
```yaml
staging-test:
  needs: unit-test
  if: github.event_name == 'pull_request'
```

**Tipos de testes a incluir no `tests_staging.py`:**
- **Mais endpoints cobertos** — endpoints que não estão nos unit tests, com BD simulada
- **Cenários de erro** — o que acontece quando um serviço gRPC está em baixo (deve devolver 503, não crashar)
- **Degradação graciosa** — quando um serviço secundário falha, o endpoint continua a responder com os dados que tem
- **Estrutura completa da resposta** — verificar todos os campos da resposta, não só o status code
- **Múltiplas dependências mockadas em simultâneo** — endpoints que chamam vários serviços gRPC

**Exemplo de teste de erro gRPC:**
```python
import grpc
from unittest.mock import patch

class MockRpcError(grpc.RpcError):
    def code(self):    return grpc.StatusCode.UNAVAILABLE
    def details(self): return "Service unavailable"

def test_endpoint_servico_em_baixo_returns_503(client):
    with patch("app.routers.meu_router._get_dados_grpc", side_effect=MockRpcError()):
        r = client.get("/meu/endpoint")
    assert r.status_code == 503
```

---

## Stage 3 — Integration Tests + Build

**Trigger:** push para `main` (após merge do PR)

**Propósito:** testes de integração reais e construção automática da imagem Docker. É aqui que entra o CD (Continuous Delivery ou Continuous Deployment).

**O que deve conter:**

**Testes de integração** — diferença chave para os stages anteriores: os serviços comunicam entre si via gRPC de forma real, ou com uma base de dados real levantada no GitHub Actions:
```yaml
services:
  postgres:
    image: postgres:16-alpine
    env:
      POSTGRES_DB: location_db
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: test
    ports:
      - 5432:5432
```

**Build e push da imagem Docker** — após os testes passarem, construir a imagem e fazer push para o Artifact Registry:
```yaml
- name: Autenticar no GCP
  uses: google-github-actions/auth@v1
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}

- name: Configurar Docker
  run: gcloud auth configure-docker europe-west1-docker.pkg.dev

- name: Build e push
  run: |
    docker build -t europe-west1-docker.pkg.dev/SEU_PROJETO/urbanpulse/SEU_SERVICO:latest .
    docker push europe-west1-docker.pkg.dev/SEU_PROJETO/urbanpulse/SEU_SERVICO:latest
```

Para o build funcionar, cada um precisa de:
1. Criar uma **Service Account** no GCP com o role `Artifact Registry Writer`
2. Descarregar o JSON das credenciais
3. Guardar o JSON como GitHub Secret com o nome `GCP_SA_KEY` (Settings → Secrets → Actions)

---

## Estrutura de ficheiros esperada por serviço

```
MicroServices/
└── meu-servico/
    ├── app/
    ├── requirements.txt
    ├── Dockerfile
    ├── tests.py           ← Stage 1 (unit tests)
    └── tests_staging.py   ← Stage 2 (staging tests)

.github/
└── workflows/
    └── ci-NUMERO.yml      ← workflow do vosso número de aluno
```

---

## Notas importantes

- **Cada aluno tem o seu próprio workflow** — o ficheiro deve chamar-se `ci-NUMERO.yml` com o vosso número de aluno, e o trigger deve ser o vosso branch individual
- **Não é necessário cobertura total** — o professor quer ver variedade de tipos de testes, não quantidade
- **O lint não deve falhar por estilo** — usem `continue-on-error: true` no segundo passo do flake8 para que avisos de formatação não bloqueiem o pipeline
- **O `TestClient` não precisa de servidor** — o FastAPI corre em memória durante os testes, não é preciso ter nenhum serviço a correr
- **Serviços com gRPC no startup** — se o vosso serviço arranca um servidor gRPC no lifespan, é preciso mockar isso antes de usar o `TestClient`:

```python
@pytest.fixture(scope="session", autouse=True)
def mock_grpc_server():
    with patch("app.grpc_server.serve_grpc", return_value=MagicMock(stop=MagicMock())):
        yield

@pytest.fixture(scope="session")
def client(mock_grpc_server):
    with TestClient(app) as c:
        yield c
```
