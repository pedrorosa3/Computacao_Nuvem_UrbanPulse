==============================
  UrbanPulse — Trip Service
  Phase 4 — Guilherme Almeida
==============================

COMO CORRER
-----------

1. Obter o ficheiro CSV limpo:
   Correr o script "taxiZones.py" (pasta taxiZonesScript) para gerar:
     yellow_tripdata_2015-01_clean.csv

2. Criar a pasta "data" dentro de "trip-service" e colocar lá:
     yellow_tripdata_2015-01_clean.csv

3. Subir os containers:
   cd trip-service
   docker-compose up --build

4. Seed da base de dados (noutro terminal, após o container estar up):
   python seed.py
   (Limitado a 10 000 viagens para testes — remover "nrows=10000" no seed.py para carga completa)

5. A API fica disponível em: http://localhost:8001
