# Phase 6 – Serverless Data Ingestion com FaaS para o Trip Service

## Introdução

O **Trip Service** é responsável por armazenar e analisar registos históricos de viagens de táxi em Nova Iorque. Atualmente, a ingestão de dados requer um processo manual: gerar o CSV localmente com o `taxiZones.py`, fazer upload para o Cloud Shell e executar o `seed.py` manualmente após os pods estarem a correr.

Este processo é moroso, propenso a erros humanos e não escalável. Se o dataset for atualizado ou se novos dados precisarem de ser ingeridos, todo o processo manual tem de ser repetido.

Para resolver este problema, foi escolhido o padrão **FaaS (Function as a Service)** com uma arquitetura **event-driven**, utilizando o **Google Cloud Functions**. Sempre que um novo ficheiro CSV é carregado para um bucket do **Google Cloud Storage (GCS)**, a função é acionada automaticamente, processa os dados e insere-os na base de dados do Trip Service — sem qualquer intervenção manual.

---

## Requisitos Não-Funcionais

- Eliminar a necessidade de ingestão manual de dados
- Reduzir o tempo de ingestão de novos datasets
- Garantir que os dados enriquecidos (`time_class`, `deviation_index`, `deviation_class`, `avg_speed_kmh`, `speed_class`, `suspicion_score`) são sempre calculados de forma consistente
- Melhorar a observabilidade do processo de ingestão através de Cloud Logging
- Minimizar custos — execução serverless com pagamento por utilização
- Garantir escalabilidade automática para ficheiros de grande dimensão

---

## Arquitetura Técnica

A arquitetura mantém o Trip Service existente e adiciona um pipeline de ingestão serverless:

- Um **bucket GCS** recebe os ficheiros CSV com os dados das viagens
- Uma **Cloud Function (Python)** é acionada automaticamente pelo evento de upload
- A função aplica a mesma lógica de enriquecimento do `seed.py` e insere os dados na **Trip DB (PostgreSQL)** no cluster GKE
- As credenciais da base de dados são armazenadas de forma segura no **Google Secret Manager**

Fluxo:

1. CSV é carregado para o bucket GCS
2. O evento de upload aciona automaticamente a Cloud Function
3. A função lê o CSV, calcula as colunas enriquecidas e valida o schema
4. Os dados são inseridos em batches de 1000 registos na Trip DB
5. O resultado é registado no Cloud Logging

---

## Plano de Implementação

### 1. Criar o bucket GCS

- Criar um bucket na região `europe-west1` para receber os ficheiros CSV
- Configurar permissões de acesso para a Cloud Function

### 2. Implementar a Cloud Function

- Escrever a função em **Python 3.11** com a mesma lógica de enriquecimento do `seed.py`
- Configurar o trigger para o evento `google.cloud.storage.object.v1.finalized`
- Implementar validação do schema do CSV antes do processamento
- Inserir dados em batches para suportar ficheiros de grande dimensão

### 3. Credenciais e Segurança

- Armazenar a password da DB no **Google Secret Manager**
- A Cloud Function acede ao Secret Manager em runtime — sem credenciais hardcoded

### 4. Deploy da Cloud Function

- Fazer deploy com `gcloud functions deploy` apontando para o bucket GCS como trigger
- Configurar variáveis de ambiente (`DB_HOST`, `DB_NAME`, `DB_USER`)
- Definir memória e timeout adequados para o tamanho do dataset

### 5. Testes

- Validar o trigger automático após upload de um CSV de teste
- Comparar o tempo de ingestão com o processo manual anterior
- Verificar os logs no Cloud Logging para confirmar o número de registos inseridos
- Testar o comportamento em caso de CSV com schema inválido