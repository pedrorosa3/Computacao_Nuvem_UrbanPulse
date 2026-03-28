from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from .. import models, database
from ..grpc_client import fetch_passenger_counts
import math


router = APIRouter()

@router.get("/tips/comparison")
def compare_tips(
    start_date: str = Query(None, description="YYYY-MM-DD"), 
    end_date: str = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(database.get_db)
):
    """UC11 — Comparação de gorjetas (Cartão vs Dinheiro)"""
    
    # Filtramos apenas viagens com fare > 0 para evitar divisão por zero
    query = db.query(
        models.Trip.payment_type,
        func.avg((models.Trip.tip_amount / models.Trip.fare_amount) * 100).label('avg_tip_pct')
    ).filter(
        models.Trip.fare_amount > 0,
        models.Trip.payment_type.in_(['card', 'cash'])
    )
    
    # Aplicar filtros de data se fornecidos
    if start_date:
        query = query.filter(models.Trip.pickup_date >= start_date)
    if end_date:
        query = query.filter(models.Trip.pickup_date <= end_date)
        
    results = query.group_by(models.Trip.payment_type).all()
    
    response = {"card_average_tip_percentage": 0.0, "cash_average_tip_percentage": 0.0}
    
    for row in results:
        if row.payment_type == 'card':
            response["card_average_tip_percentage"] = round(row.avg_tip_pct, 2)
        elif row.payment_type == 'cash':
            response["cash_average_tip_percentage"] = round(row.avg_tip_pct, 2)
            
    response["difference_points"] = round(
        response["card_average_tip_percentage"] - response["cash_average_tip_percentage"], 2
    )
    
    return response


@router.get("/distribution")
def payment_distribution(db: Session = Depends(database.get_db)):
    """UC12 — Distribuição de métodos de pagamento e zonas atípicas"""
    
    total_trips = db.query(func.count(models.Trip.id)).scalar()
    
    if total_trips == 0:
        return {"message": "Sem dados disponíveis."}
        
    # Distribuição Global
    distribution_query = db.query(
        models.Trip.payment_type,
        func.count(models.Trip.id).label('count')
    ).group_by(models.Trip.payment_type).all()
    
    global_dist = {
        row.payment_type: round((row.count / total_trips) * 100, 2) 
        for row in distribution_query
    }
    
    return {
        "overall_distribution": global_dist,
        "atypical_zones": "Funcionalidade de zonas atípicas em desenvolvimento..." 
        # (Aqui poderias agrupar por zona e comparar com a global_dist)
    }


@router.get("/zones/tipping-score")
def ranking_tipping_score(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(database.get_db)
):
    """UC13 — Ranking de zonas por Tipping Score"""
    
    # Calcula a % média de gorjeta por zona (apenas para pagamentos com cartão, 
    # já que dinheiro muitas vezes não regista gorjeta no sistema)
    results = db.query(
        models.Trip.pickup_zone_id,
        func.avg((models.Trip.tip_amount / models.Trip.fare_amount) * 100).label('score')
    ).filter(
        models.Trip.fare_amount > 0,
        models.Trip.payment_type == 'card'
    ).group_by(
        models.Trip.pickup_zone_id
    ).order_by(
        func.avg((models.Trip.tip_amount / models.Trip.fare_amount) * 100).desc()
    ).limit(limit).all()
    
    ranking = [
        {"zone_id": row.pickup_zone_id, "score": round(row.score, 2)} 
        for row in results
    ]
    
    return ranking

@router.get("/tips/passenger-correlation")
def passenger_tip_correlation(
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date: str = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(database.get_db)
):
    """UC14 — Correlação entre passageiros e gorjeta (Integração gRPC)"""
    
    # 1. Vamos buscar os IDs das viagens e as gorjetas à tua base de dados
    query = db.query(
        models.Trip.id, 
        models.Trip.fare_amount, 
        models.Trip.tip_amount
    ).filter(models.Trip.fare_amount > 0)
    
    if start_date:
        query = query.filter(models.Trip.pickup_date >= start_date)
    if end_date:
        query = query.filter(models.Trip.pickup_date <= end_date)
        
    # Limitamos a 500 para o teste ser rápido e não sobrecarregar a rede
    trips = query.limit(500).all() 
    
    if not trips:
        return {"message": "Sem dados suficientes na base de dados."}
        
    trip_ids = [t.id for t in trips]
    
    # 2. Magia do Microserviço: Pedimos os passageiros ao serviço do Guilherme!
    passenger_data = fetch_passenger_counts(trip_ids)
    
    if not passenger_data:
        return {
            "status": "A aguardar integração",
            "message": "O Trip Service do Guilherme não respondeu ou está offline. Tenta mais tarde!"
        }
        
    # 3. Cruzar os dados (Match entre a DB e a resposta gRPC)
    tips_pct = []
    passengers = []
    
    for t in trips:
        if t.id in passenger_data:
            tip_pct = (t.tip_amount / t.fare_amount) * 100
            tips_pct.append(tip_pct)
            passengers.append(passenger_data[t.id])
            
    # 4. Fórmula Matemática da Correlação de Pearson
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
    
    # Classificação textual
    if abs(correlation) < 0.3: classif = "Fraca"
    elif abs(correlation) < 0.7: classif = "Moderada"
    else: classif = "Forte"
    
    return {
        "analyzed_trips": len(passengers),
        "correlation_coefficient": round(correlation, 4),
        "description": f"Correlação {classif} {'Positiva' if correlation > 0 else 'Negativa'}."
    }

