Para correr, ir até à loc da pasta no PowerShell, e correr: docker-compose up --build

Para o container da DB, estou a usar uma image oficial do Postgre.

As tabelas são criadas automaticamente através do init.sql quando o container arranca.

O ficheiro do dataset está dentro da pasta data. Para o payment-db conter os dados necessários, temos que correr o seed.py.

O seed.py só pode ser corrido depois do container estar ligado. É um script que envia dados do meu pc para o container, via porta 5434 (usei a 5434 para não chocar com o Location Service).

O seed.py está limitado a 10000 viagens, só para testes. Depois desbloquear.

Depois de correr o seed.py, a payment-db está pronta para ser utilizada pelo payment service.

# Relativamente ao container payment-api:

A image que utiliza é a definida no Dockerfile. Copia toda a pasta /app para dentro do container, instala todas as dependências necessárias, e fica preparado para receber pedidos.

O main.py utiliza o FastAPI para iniciar a API propriamente dita.

O database.py é o script responsável por fazer a ligação entre o container payment-api e o container payment-db. Este último apenas pode ser acedido através do payment-api.

Os routers é onde está a lógica da aplicação propriamente dita (UC11, UC12, UC13).

# Como correr:

Criar a pasta data no diretório payment-service. Dentro dessa pasta data, colocar o ficheiro:

yellow_tripdata_2015-01_clean.csv

# Comandos para correr no PowerShell:

cd "C:\...\Cloud-Computing\phase4\payment-service"

docker-compose up --build

python seed.py - Noutro terminal. Este script é para colocar dados na DB. Antes de o correr, a DB está vazia.

# Alguns endpoints para testar:

http://localhost:8006/api/v1/payments/tips/comparison

http://localhost:8006/api/v1/payments/distribution

http://localhost:8006/api/v1/payments/zones/tipping-score?limit=5
