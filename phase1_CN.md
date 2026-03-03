# Phase 1 - Group 4

## Dataset identification

**URL:** https://www.kaggle.com/datasets/elemento/nyc-yellow-taxi-trip-data
**Topic:** Registos de viagens de taxis em Nova Iorque (pickups, dropoffs, custos, gorjetas e formas de pagamento)
**Size:** 7.39gb (4 ficheiros, cada um com cerca de 1.8gb)

## Business capabilities

A UrbanPulse é uma plataforma de análise histórica de dados de mobilidade urbana oferecida como serviço. 
Os clientes utilizam os padrões históricos fornecidos como baseline para os seus próprios sistemas de decisão (estimativa de preços, gestão de frota e planeamento urbano.)

- **Trip Intelligence** — Análise de padrões históricos de viagens urbanas: distâncias, durações e rotas.
- **Revenue & Pricing Intelligence** — Padrões históricos de tarifas e receitas por zona, período e tipo de serviço.
- **Payment & Tipping Analytics** — Comportamento de pagamento em serviços de transporte urbano por zona e método.
- **Demand Intelligence** — Padrões temporais e geográficos de procura de transporte urbano por zona e período.

## Use Cases

### Guilherme — Trip Service
- UC01 — Classificação das viagens por hora do dia (peak, off-peak, night)
- UC02 — Índice de desvio de rota com classificação efficient/moderate/inefficient
- UC03 — Velocidade média das viagens por zona e período do dia (km/h), com classificação automática em slow, normal ou fast com base em thresholds históricos
- UC18 — Coeficiente entre duração e gorjeta (Ver se viagens longas têm mais gorjeta) *(chama Trip Service + Payment Service)*
- UC20 — Deteção de viagens com valores suspeitos (Uma viagem de 2km a custar 50p ou assim.) 
  *(chama Trip Service + Revenue Service)*

### Diogo — Location Service
- UC04 — Ranking de zonas com quota de mercado
- UC05 — Top zonas de dropoff com percentagem por destino
- UC06 — Pares origem-destino com índice de afinidade entre zonas
- UC07 — Perfil completo de zona com score de atratividade *(chama Demand Service)*
- UC19 — Score de performance por fornecedor 
  *(chama Trip Service + Revenue Service + Payment Service)*

### Chico — Revenue Service
- UC08 — Tarifa média por zona com desvio face à média global
- UC09 — Decomposição percentual da receita por viagem (Do preço total, quanto corresponde à tarifa base, quanto corresponde à gorjeta etc...)
- UC10 — Preço por km por zona *(chama Trip Service)*
- UC15 — Matriz hora vs dia com identificação de horas de ponta.
- UC16 — Evolução mensal com variação percentual e tendência

### Pedro — Payment Service
- UC11 — Comparação estatística de gorjeta entre cartão e dinheiro
- UC12 — Distribuição de métodos de pagamento com deteção de zonas atípicas
- UC13 — Ranking de zonas por tipping score
- UC14 — Correlação passageiros vs gorjeta *(chama Trip Service)*
- UC17 — Instabilidade de procura por zona (Quanto a procura varia ao longo do dia)