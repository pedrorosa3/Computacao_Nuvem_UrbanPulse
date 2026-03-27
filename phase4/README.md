# UrbanPulse — Payment Service (Phase 4)
**Autor:** Pedro Rosa
**Módulo:** Pagamentos e Gorjetas (UC11, UC12, UC13, UC14)

Este diretório contém a implementação do microserviço de **Payment** para o projeto UrbanPulse, desenvolvido em FastAPI, com base de dados PostgreSQL e orquestrado com Docker.

## 📌 Pré-requisitos e Setup de Dados

Para a base de dados (`payment-db`) conter os dados necessários, utilizamos um script de ingestão (`seed.py`).



1. Obter o ficheiro CSV limpo:
   Correr o script "taxiZones.py" (pasta taxiZonesScript) para gerar:
     yellow_tripdata_2015-01_clean.cs

2. Criar a pasta "data" dentro de "payment-service" e colocar lá:
     yellow_tripdata_2015-01_clean.csv

3. Fazer o docker compose up --build na diretoria payment-service:

4. Noutro terminal na mesma diretoria fazer python seed.py - (Limitado a 10 000 viagens para testes — remover "nrows=10000" no seed.py para carga completa)

5. A API fica disponível em: http://localhost:8001/docs

