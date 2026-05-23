from fastapi_cache.decorator import cache
import math
from fastapi import APIRouter, Depends, Query, HTTPException
from app.bigquery_client import get_bq_client # <-- Importa a ligação que criámos há bocado!

router = APIRouter()

# Dicionário auxiliar para traduzir os códigos de pagamento do BigQuery
PAYMENT_TYPES = {
    1: "Credit card",
    2: "Cash",
    3: "No charge",
    4: "Dispute",
    5: "Unknown",
    6: "Voided trip"
}

@router.get("/tips/comparison")
@cache(expire=3600) # Guarda o resultado por 1 hora
def compare_tips(
    start_date: str = Query(None, description="YYYY-MM-DD"), 
    end_date: str = Query(None, description="YYYY-MM-DD")
):
    """UC11 — Comparação de gorjetas (Cartão vs Dinheiro)"""
    client = get_bq_client()
    
    # Filtro de datas para o BigQuery
    date_filter = ""
    if start_date and end_date:
        date_filter = f"AND DATE(tpep_pickup_datetime) BETWEEN '{start_date}' AND '{end_date}'"
        
    # No BigQuery: 1 = Cartão, 2 = Dinheiro
    query = f"""
        SELECT 
            payment_type,
            AVG((tip_amount / fare_amount) * 100) as avg_tip_pct
        FROM `computacaonuvem60294.taxi_demand.trips`
        WHERE fare_amount > 0
          AND payment_type IN (1, 2)
          {date_filter}
        GROUP BY payment_type
    """
    
    try:
        results = list(client.query(query).result())
        
        response = {"card_average_tip_percentage": 0.0, "cash_average_tip_percentage": 0.0}
        
        for row in results:
            if row.payment_type == 1: # Cartão
                response["card_average_tip_percentage"] = round(row.avg_tip_pct, 2)
            elif row.payment_type == 2: # Dinheiro
                response["cash_average_tip_percentage"] = round(row.avg_tip_pct, 2)
                
        response["difference_points"] = round(
            response["card_average_tip_percentage"] - response["cash_average_tip_percentage"], 2
        )
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/distribution")
@cache(expire=3600) # Guarda o resultado por 1 hora
def payment_distribution():
    """UC12 — Distribuição de métodos de pagamento e zonas atípicas"""
    client = get_bq_client()
    
    # Fazemos as contas todas diretamente no SQL do BigQuery usando funções de janela (OVER)
    query = """
        SELECT 
            payment_type,
            COUNT(*) as count,
            (COUNT(*) / SUM(COUNT(*)) OVER()) * 100 as percentage
        FROM `computacaonuvem60294.taxi_demand.trips`
        GROUP BY payment_type
        ORDER BY percentage DESC
    """
    
    try:
        results = list(client.query(query).result())
        
        global_dist = {}
        for row in results:
            # Traduz o ID numérico para o nome por extenso
            metodo_nome = PAYMENT_TYPES.get(row.payment_type, f"Other ({row.payment_type})")
            global_dist[metodo_nome] = round(row.percentage, 2)
            
        return {
            "overall_distribution": global_dist,
            "atypical_zones": "Funcionalidade de zonas atípicas em desenvolvimento..." 
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zones/tipping-score")
@cache(expire=3600) # Guarda o resultado por 1 hora
def ranking_tipping_score(limit: int = Query(10, ge=1, le=100)):
    """UC13 — Ranking de zonas por Tipping Score"""
    client = get_bq_client()
    
    # Usa payment_type = 1 (Cartão) e exclui zonas nulas
    query = f"""
        SELECT 
            pickup_zone_id,
            AVG((tip_amount / fare_amount) * 100) as score
        FROM `computacaonuvem60294.taxi_demand.trips`
        WHERE fare_amount > 0
          AND payment_type = 1
          AND pickup_zone_id IS NOT NULL
        GROUP BY pickup_zone_id
        ORDER BY score DESC
        LIMIT {limit}
    """
    
    try:
        results = list(client.query(query).result())
        
        ranking = [
            {"zone_id": int(row.pickup_zone_id), "score": round(row.score, 2)} 
            for row in results
        ]
        return ranking
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tips/passenger-correlation")
@cache(expire=3600) # Guarda o resultado por 1 hora
def passenger_tip_correlation(
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date: str = Query(None, description="YYYY-MM-DD")
):
    """UC14 — Correlação entre passageiros e gorjeta (Via BigQuery DW)"""
    client = get_bq_client()
    
    date_filter = ""
    if start_date and end_date:
        date_filter = f"AND DATE(tpep_pickup_datetime) BETWEEN '{start_date}' AND '{end_date}'"
        
    # Centralizamos a leitura analítica no Data Warehouse.
    # Lemos apenas as viagens com passageiros válidos e com pagamento em cartão (onde há registo de gorjeta)
    query = f"""
        SELECT 
            passenger_count, 
            (tip_amount / fare_amount) * 100 as tip_pct
        FROM `computacaonuvem60294.taxi_demand.trips`
        WHERE fare_amount > 0
          AND payment_type = 1
          AND passenger_count > 0
          {date_filter}
        LIMIT 2000
    """
    
    try:
        results = list(client.query(query).result())
        
        if not results:
            return {"message": "Sem dados suficientes no BigQuery para o período selecionado."}
            
        passengers = [row.passenger_count for row in results]
        tips_pct = [row.tip_pct for row in results]
        
        # Fórmula Matemática da Correlação de Pearson
        def calculate_pearson(x, y):
            n = len(x)
            if n < 2: return 0.0
            mean_x = sum(x) / n
            mean_y = sum(y) / n
            numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
            sum_sq_x = sum((xi - mean_x)**2 for xi in x)
            sum_sq_y = sum((yi - mean_y)**2 for yi in y)
            denominator = math.sqrt(sum_sq_x * sum_sq_y)
            return numerator / denominator if denominator != 0 else 0.0
            
        correlation = calculate_pearson(passengers, tips_pct)
        
        if abs(correlation) < 0.3: classif = "Fraca"
        elif abs(correlation) < 0.7: classif = "Moderada"
        else: classif = "Forte"
        
        return {
            "analyzed_trips": len(passengers),
            "correlation_coefficient": round(correlation, 4),
            "description": f"Correlação {classif} {'Positiva' if correlation > 0 else 'Negativa'}."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
