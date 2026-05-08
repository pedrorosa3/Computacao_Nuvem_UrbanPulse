import os
import json
from google.cloud import bigquery
from google.oauth2 import service_account

def get_bq_client():
    # 1. Descobre automaticamente a pasta onde este script (bigquery_client.py) está guardado
    pasta_atual = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Junta o caminho da pasta com o nome do teu ficheiro JSON
    caminho_para_chave = os.path.join(pasta_atual, "a.json") 
    
    with open(caminho_para_chave) as source:
        json_file = json.load(source)
    
    credentials = service_account.Credentials.from_service_account_info(json_file)
    
    client = bigquery.Client(
        credentials=credentials, 
        project='computacaonuvem60294', 
        location='europe-west4'
    )
    return client