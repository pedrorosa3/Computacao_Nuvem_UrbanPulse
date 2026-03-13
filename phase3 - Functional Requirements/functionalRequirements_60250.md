# Functional Requirements — Phase 3

Diogo Cordeiro de Sousa | 60250

## UC04 — Ranking de Zonas de Pickup com Quota de Mercado

- FR-04.1 — O sistema devolve as zonas de pickup ordenadas por volume de trips, com o market share de cada zona calculado em percentagem do total de trips do período.
- FR-04.2 — O sistema suporta filtragem por período temporal e limitação do número de resultados.
- FR-04.3 — O sistema devolve o total de trips do período e o período aplicado na resposta, para permitir verificação dos valores calculados.

## UC05 — Top Zonas de Dropoff com Percentagem por Destino

- FR-05.1 — Para uma zona de pickup específica, o sistema devolve os destinos mais frequentes com a percentagem de trips que cada destino representa face ao total de saídas dessa zona.
- FR-05.2 — O sistema suporta filtragem por período temporal e limitação do número de resultados.
- FR-05.3 — O sistema devolve os metadados da zona de origem e o total de trips de saída, e retorna erro 404 se a zona não existir.

## UC06 — Pares Origem-Destino com Índice de Afinidade

- FR-06.1 — O sistema identifica e devolve os pares de zonas com relações estruturalmente mais fortes, medidas pelo affinity index: `trips(A→B) / (total_saídas_A × total_entradas_B)`. Valores acima de 1.0 indicam uma ligação mais forte do que o esperado.
- FR-06.2 — O sistema exclui pares com volume insuficiente e suporta filtragem por período temporal.
- FR-06.3 — O sistema devolve, para cada par, a frequência relativa como percentagem do total de trips da cidade, e inclui o período aplicado na resposta.

## UC07 — Perfil Completo de Zona com Score de Atratividade

- FR-07.1 — O sistema agrega, para uma zona, métricas de volume de trips, métricas financeiras (fare, tip) e padrões de procura obtidos do Demand Service, num único perfil.
- FR-07.2 — O sistema calcula um attractiveness score (0–100) como composição ponderada do volume de trips (40%), gorjeta média (35%) e intensidade de procura em pico (25%), com classificação low/medium/high.
- FR-07.3 — O sistema suporta filtragem por período temporal e retorna erro 404 se a zona não existir.

## UC19 — Comparação de Padrões de Mobilidade entre Zonas Ricas e Periféricas

- FR-19.1 — O sistema compara métricas de mobilidade (trips, distância, fare, tip, volatilidade) entre zonas afluentes (Manhattan Yellow Zone) e periféricas (Bronx, Staten Island, Boro Zones), categorias definidas server-side.
- FR-19.2 — Para cada dimensão, o sistema calcula o mobility gap: `(valor_afluente − valor_periférico) / valor_periférico × 100`, e identifica as dimensões com maior desigualdade.
- FR-19.3 — O sistema agrega dados de múltiplos serviços (Revenue, Payment, Demand, Location) via chamadas REST internas, e suporta filtragem por período temporal.

## UC23 — Atualização de uma Viagem Existente

- FR-23.1 — O sistema aplica atualizações parciais a um registo de viagem existente, mantendo os campos não fornecidos inalterados.
- FR-23.2 — Após qualquer atualização, o sistema re-aplica automaticamente todas as classificações de enriquecimento (UC01, UC02, UC03, UC20) ao registo atualizado.
- FR-23.3 — O sistema retorna erro 404 se a viagem não existir, erro 422 se os valores atualizados resultarem numa viagem inválida, e erro 400 se o request body estiver vazio ou mal formado.
