# Functional Requirements — Phase 3
Pedro Rosa | Payment Service

## UC11 — Comparação Estatística de Gorjeta entre Cartão e Dinheiro

- FR-11.1 — O sistema calcula e devolve a média de gorjeta (em percentagem face à tarifa base) agrupada por método de pagamento (Cartão vs Dinheiro).

- FR-11.2 — O sistema calcula a diferença percentual (points) entre os dois métodos para evidenciar qual gera maior gorjeta.

- FR-11.3 — O sistema suporta filtragem temporal (start_date, end_date) e espacial (zone_id opcional) para permitir análises localizadas.

## UC12 — Distribuição de Métodos de Pagamento com Deteção de Zonas Atípicas

- FR-12.1 — O sistema devolve a distribuição global em percentagem de todos os métodos de pagamento registados no período selecionado.

- FR-12.2 — O sistema identifica e devolve uma lista de "zonas atípicas", definidas como zonas onde a utilização de um método de pagamento diverge em mais de 20% (threshold configurável) da média global.

- FR-12.3 — O sistema suporta filtragem por período temporal e devolve erro 400 se os parâmetros de data forem inválidos.

## UC13 — Ranking de Zonas por Tipping Score

- FR-13.1 — O sistema calcula um tipping score (0-100) para cada zona, baseado na propensão histórica dos passageiros para deixar gorjetas acima da média da cidade.

- FR-13.2 — O sistema devolve as zonas ordenadas de forma decrescente pelo seu score.

- FR-13.3 — O sistema suporta limitação do número de resultados (Top N) e filtragem por período temporal.

## UC14 — Correlação Passageiros vs Gorjeta

- FR-14.1 — O sistema calcula o coeficiente de correlação (ex: Pearson) entre o número de passageiros e a percentagem da gorjeta.

- FR-14.2 — O Payment Service comunica internamente via gRPC com o Trip Service para obter os dados do número de passageiros das viagens em análise.

- FR-14.3 — O sistema devolve o valor numérico da correlação acompanhado de uma classificação textual (fraca, moderada, forte).

## UC17 — Instabilidade de Procura por Zona

- FR-17.1 — O sistema calcula a variância do volume de viagens ao longo das 24 horas do dia para uma zona específica, gerando um índice de instabilidade.

- FR-17.2 — O sistema identifica as horas de pico anómalas e classifica a zona em: Stable, Moderate ou Highly Unstable.

- FR-17.3 — O sistema devolve erro 404 se a zona solicitada não existir ou não tiver dados suficientes para análise estatística.


## Descrição da arquitetura
O nosso sistema foi desenhado com base numa arquitetura orientada a microserviços, dividindo-se em seis componentes autónomos: Trips, Location, Revenue, Payment, Demand e Analytics. Para gerir a elevada volumetria do nosso dataset e garantir um forte desacoplamento entre os domínios, implementámos o padrão arquitetural 'Database per service'. O tráfego externo interage com a plataforma através de uma API REST, sendo posteriormente canalizado para um gRPC Gateway que atua como router interno para o microserviço correspondente. Para otimizar a performance, a comunicação inter-serviços (quando um serviço precisa de consultar outro) é feita de forma direta (ponto a ponto), dispensando a passagem pelo gateway central. Esta abordagem garante que a aplicação se mantém altamente modular, tolerante a falhas e facilmente escalável.
