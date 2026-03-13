# Functional Requirements — Phase 3

Guilherme Almeida | 60264

---

## UC01 — Classificação das Viagens por Hora do Dia

- FR-01.1 — O sistema classifica cada viagem numa de três categorias temporais — peak (horas de ponta), off-peak (horas normais) e night (período noturno) — com base na hora de início da viagem.
- FR-01.2 — O sistema suporta filtragem por período temporal e devolve, para cada categoria, o volume de viagens e a sua percentagem face ao total do período.
- FR-01.3 — O sistema devolve os thresholds horários aplicados e o período considerado na resposta, para permitir a verificação da classificação.

---

## UC02 — Índice de Desvio de Rota

- FR-02.1 — O sistema calcula, para cada viagem, um índice de desvio de rota definido como distância_percorrida / distância_direta, e classifica a viagem em efficient, moderate ou inefficient, com base em thresholds pré-definidos.
- FR-02.2 — O sistema suporta filtragem por período temporal e por zona, e devolve a distribuição das classificações com contagens e percentagens por categoria.
- FR-02.3 — O sistema devolve os thresholds de classificação aplicados e retorna erro se a viagem ou zona especificada não existir.

---

## UC03 — Velocidade Média das Viagens por Zona e Período do Dia

- FR-03.1 — O sistema calcula a velocidade média em km/h das viagens agrupadas por zona e por período do dia (peak, off-peak, night), e classifica automaticamente cada grupo em slow, normal ou fast com base em thresholds históricos dos dados existentes.
- FR-03.2 — O sistema suporta filtragem por período temporal e por zona específica, e devolve, para cada combinação zona/período, a velocidade média, o número de viagens consideradas e a classificação atribuída.
- FR-03.3 — O sistema devolve os thresholds históricos utilizados na classificação e retorna erro se a zona especificada não existir.

---

## UC18 — Coeficiente entre Duração e Gorjeta

- FR-18.1 — O sistema calcula o coeficiente de correlação entre a duração da viagem e o valor da gorjeta, segmentando a análise por intervalos de duração, de forma a identificar se viagens mais longas tendem a gerar gorjetas proporcionalmente maiores.
- FR-18.2 — O sistema suporta filtragem por período temporal e devolve, para cada segmento de duração, a gorjeta média, o número de viagens e o coeficiente de correlação calculado.
- FR-18.3 — O sistema devolve uma interpretação do coeficiente (correlação fraca, moderada ou forte) e o período considerado na resposta.

---

## UC20 — Deteção de Viagens com Valores Suspeitos

- FR-20.1 — O sistema deteta viagens com valores anómalos aplicando regras de validação estatística, nomeadamente: desproporção face à distância percorrida, gorjeta que excede uma percentagem anormal do fare, distância ou duração incompatíveis entre si, e combinações de valores que se desviem significativamente da distribuição histórica.
- FR-20.2 — O sistema classifica cada anomalia detetada por tipo e grau de suspeição, e suporta filtragem por período temporal e por tipo de anomalia.
- FR-20.3 — O sistema devolve, para cada viagem suspeita, os campos que motivaram a classificação, os valores esperados com base no histórico, e o score de suspeição atribuído.

---

## UC21 — Remoção de Viagens com Dados Inválidos ou Suspeitos

- FR-21.1 — O sistema remove permanentemente registos de viagens que contenham dados inválidos ou que tenham sido sinalizados como suspeitos pelo UC20, mediante confirmação explícita do pedido.
- FR-21.2 — O sistema suporta remoção individual por ID de viagem e remoção em lote com base em critérios de filtragem.
- FR-21.3 — O sistema retorna erro 404 se a viagem não existir, erro 409 se a viagem não estiver marcada como inválida ou suspeita, e devolve um sumário com o número de registos removidos e os IDs afetados.

---

## UC22 — Submissão de uma Nova Viagem para Análise

- FR-22.1 — O sistema aceita a submissão de um novo registo de viagem com os campos obrigatórios (zona de pickup, zona de dropoff, distância, duração, fare) e, após persistência, aplica automaticamente as classificações de enriquecimento.
- FR-22.2 — O sistema valida os dados submetidos antes da persistência, rejeitando valores fora dos intervalos admissíveis ou combinações logicamente inválidas.
- FR-22.3 — O sistema retorna erro 422 se os dados forem inválidos, erro 400 se o request body estiver vazio ou mal formado, e devolve o registo completo com as classificações aplicadas em caso de sucesso.
