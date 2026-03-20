Para correr, ir até à loc da pasta no PowerShell, e correr: "docker-compose up"

Para o container da DB, estou a usar uma image oficial do Postgre.

As tabelas são criadas automaticamente através do "init.sql" quando o container arranca.

O ficheiro do dataset está dentro da pasta "data". Para o location-db conter os dados necessários, temos que correr o "seed.py"

O seed.py só pode ser corrido depois do container estar ligado. É um script que envia dados do meu pc para o container, via porta 5433, default do Postgre.

O seed.py está limitado a 10000 viagens, só para testes. Depois desbloquear.

Depois de correr o seed.py, a location-db está pronta para ser utilizada pelo location service.