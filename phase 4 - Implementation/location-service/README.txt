NOTA (passwords e dependências):
- As passwords das BDs estão no ficheiro .env da pasta "phase 4 - Implementation" (copiar .env.example para .env e definir as passwords).
- O docker compose deste serviço tem de ser corrido com: docker compose --env-file ../.env up --build
- Antes do seed.py: pip install pandas sqlalchemy psycopg2-binary python-dotenv numpy
- Nesta fase, os CSV ficam na pasta data/ do serviço.

Para correr, ir até à loc da pasta no PowerShell, e correr: docker compose --env-file ../.env up --build

Para o container da DB, estou a usar uma image oficial do Postgre.

As tabelas são criadas automaticamente através do "init.sql" quando o container arranca.

O ficheiro do dataset está dentro da pasta "data". Para o location-db conter os dados necessários, temos que correr o "seed.py"

O seed.py só pode ser corrido depois do container estar ligado. É um script que envia dados do meu pc para o container, via porta 5433.

O seed.py está limitado a 10000 viagens, só para testes. Depois desbloquear.

Depois de correr o seed.py, a location-db está pronta para ser utilizada pelo location service.


Relativamente ao container "location-api":

A image que utiliza é a definida no Dockerfile. Copia toda a pasta /app para dentro do container, instala todas as dependências necessárias, e fica preparado
para receber pedidos na porta 8000.

O main.py utiliza o FastAPI para iniciar a API propriamente, dita.

O database.py é o script responsável por fazer a ligação entre o container location-api e o container location-db. Este último apenas pode ser acedido através do location-api.

Os routers é onde está a lógica da aplicação propriamente dita. Para já fiz apenas os que utilizam dados que estão presentes na location-db. 


Como correr:


Obter o ficheiro "yellow_tripdata_2015-01_clean.csv":
-Correr o "taxiZones.py", script localizado na pasta "taxiZonesScript", que vai gerar o ficheiro "yellow_tripdata_2015-01_clean.csv",
ou outro à nossa escolha.


Criar a pasta "data" no diretório "location-service". Dentro dessa pasta data, colocar os ficheiros:
-taxi_zone_lookup.csv  (Pode ser encontrado dentro da pasta "taxiZonesScript")
-yellow_tripdata_2015-01_clean.csv


Comandos para correr no PowerShell:
cd "<pasta do repositório>\phase 4 - Implementation\location-service"
docker compose --env-file ../.env up --build
python seed.py - Noutro terminal. Este script é para colocar dados na DB. Antes de o correr, a DB está vazia.

Alguns endpoints para testar:
http://localhost:8000/locations/pickup/ranking 
http://localhost:8000/locations/161/dropoffs - Podemos substituir o "161" por qualquer outro ID de zona.
http://localhost:8000/locations/pairs?min_trips=1 - O "pairs?min_trips=1" está no endpoint porque como estou só a testar com 10000 viagens, tenho que pôr um minimo muito baixo para aparecer algum resultado.
http://localhost:8000/locations/pickup/ranking?start_date=2015-01-01&end_date=2015-01-15&limit=5
http://localhost:8000/locations/161/dropoffs?start_date=2015-01-01&end_date=2015-01-15

Devem dar erro:
http://localhost:8000/locations/pickup/ranking?start_date=2015-03-01&end_date=2015-01-01
http://localhost:8000/locations/9999/dropoffs