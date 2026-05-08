## 1 - Implementação da Segurança (Kubernetes Secrets)

Em vez de teres a password no YAML, vamos criar um "cofre" no Kubernetes.

Passo A: Criar o ficheiro payment-secrets.yaml
Primeiro, tens de converter os teus dados para Base64 no terminal do Cloud Shell:

echo -n "nome" | base64
echo -n "pass" | base64


Colocar no ficheiro payment-secrets.yaml o resultado.


Alterar no payment-service-deployment e no payment-db-deployment para usar o env do kubernettes secrets.


## 2 - Redis

Criar server no redis.yaml.

Colocar os imports no main.py e nos routers colocar a cache para 1 hora em cada route.

## 3 - Prometeus

Colocar no main.py :

from prometheus_fastapi_instrumentator import Instrumentator

# Logo abaixo da criação da app = FastAPI()
Instrumentator().instrument(app).expose(app)

Não esquecer de colocar nos requirements, estes novos requirements.
