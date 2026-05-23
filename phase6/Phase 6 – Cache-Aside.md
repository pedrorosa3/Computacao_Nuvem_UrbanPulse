# Phase 6 – Cache-Aside para Demand e Revenue

## Introdução

Os microserviços **Demand** e **Revenue** são responsáveis por fornecer dados analíticos e agregações sobre o dataset de viagens. Estes serviços executam consultas potencialmente pesadas sobre bases de dados PostgreSQL, sendo provável que múltiplos pedidos repitam os mesmos cálculos com frequência.

Para melhorar o desempenho e a escalabilidade do sistema, foi escolhido o padrão **cache-aside**, uma solução simples e eficaz para reduzir a carga sobre a base de dados e diminuir a latência das respostas.

Neste padrão, os dados são armazenados temporariamente numa cache (Redis), permitindo que pedidos repetidos sejam respondidos diretamente sem necessidade de novas consultas à base de dados.

---

## Requisitos Não-Funcionais

- Reduzir a latência de resposta para pedidos repetidos  
- Diminuir a carga nas bases de dados PostgreSQL  
- Melhorar a escalabilidade dos microserviços  
- Garantir consistência eventual dos dados  
- Minimizar alterações na arquitetura existente  

---

## Arquitetura Técnica

A arquitetura mantém os microserviços existentes e adiciona um componente de cache:

- Um novo serviço **Redis** é introduzido no cluster Kubernetes  
- Os microserviços `demand-api` e `revenue-api` passam a consultar o Redis antes da base de dados  
- Em caso de *cache miss*, os dados são obtidos do PostgreSQL e armazenados na cache com um tempo de expiração (TTL)  

Fluxo:

1. Pedido chega ao microserviço  
2. Verificação da cache (Redis)  
3. Se existir → resposta imediata  
4. Se não existir → consulta à base de dados → guardar na cache → responder  

---

## Plano de Implementação

### 1. Deploy do Redis

- Criar um deployment para Redis no Kubernetes  
- Expor através de um Service interno  
- Definir variáveis de ambiente (`REDIS_URL`) nos microserviços  

### 2. Integração nos Microserviços

- Adicionar cliente Redis (ex: `redis-py`)  
- Implementar lógica cache-aside nos endpoints mais utilizados  
- Definir chaves de cache com base nos parâmetros dos pedidos  


### 3. Configuração de TTL

- Definir tempo de permanência em cache
- Ajustar conforme a frequência de atualização dos dados  

### 4. Testes

- Comparar tempo de resposta com e sem cache  
- Validar comportamento em cache hit e cache miss  
