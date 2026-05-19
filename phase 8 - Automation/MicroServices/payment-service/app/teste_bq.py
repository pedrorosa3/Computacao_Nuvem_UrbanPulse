from google.cloud import bigquery
from google.oauth2 import service_account
import json

# 1. Carregar a chave JSON que descarregaste
caminho_para_chave = "a.json"
with open(caminho_para_chave) as source:
    json_file = json.load(source)

# 2. Criar as credenciais
credentials = service_account.Credentials.from_service_account_info(json_file) # [cite: 515]

# 3. Ligar ao BigQuery (Muda o PROJECT-ID e a REGION!)
client = bigquery.Client(credentials=credentials, project='computacaonuvem60294', location='europe-west4') 

# 4. Fazer uma query de teste (Muda o nome do dataset/tabela se puseste outro)
# 4. Fazer uma query de teste para ver as colunas todas
query = """
    SELECT * FROM `computacaonuvem60294.taxi_demand.trips` 
    LIMIT 1
"""

print("A contactar o BigQuery...")
query_job = client.query(query)
resultados = list(query_job.result()) 

print("\nSucesso! Aqui está a primeira viagem e os nomes verdadeiros das colunas:")
for linha in resultados:
    # Transformamos a linha num dicionário para ser mais fácil ler as colunas
    print(dict(linha))