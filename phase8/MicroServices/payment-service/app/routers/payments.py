import math
from fastapi import APIRouter, Query
from fastapi_cache.decorator import cache
from sqlalchemy import func
from app.database import SessionLocal
from app.models import Trip

router = APIRouter()


@router.get("/tips/comparison")
@cache(expire=3600)
def compare_tips(
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date:   str = Query(None, description="YYYY-MM-DD"),
):
    """UC11 — Comparação de gorjetas (Cartão vs Dinheiro)"""
    db = SessionLocal()
    try:
        query = db.query(
            Trip.payment_type,
            func.avg(Trip.tip_amount / Trip.fare_amount * 100).label("avg_tip_pct"),
        ).filter(Trip.fare_amount > 0, Trip.payment_type.in_(["card", "cash"]))

        if start_date:
            query = query.filter(Trip.pickup_date >= start_date)
        if end_date:
            query = query.filter(Trip.pickup_date <= end_date)

        results = query.group_by(Trip.payment_type).all()

        response = {"card_average_tip_percentage": 0.0, "cash_average_tip_percentage": 0.0}
        for row in results:
            if row.payment_type == "card":
                response["card_average_tip_percentage"] = round(row.avg_tip_pct or 0.0, 2)
            elif row.payment_type == "cash":
                response["cash_average_tip_percentage"] = round(row.avg_tip_pct or 0.0, 2)

        response["difference_points"] = round(
            response["card_average_tip_percentage"] - response["cash_average_tip_percentage"], 2
        )
        return response
    finally:
        db.close()


@router.get("/distribution")
@cache(expire=3600)
def payment_distribution():
    """UC12 — Distribuição de métodos de pagamento"""
    db = SessionLocal()
    try:
        total = db.query(func.count(Trip.id)).scalar() or 0
        results = db.query(
            Trip.payment_type,
            func.count(Trip.id).label("count"),
        ).group_by(Trip.payment_type).order_by(func.count(Trip.id).desc()).all()

        distribution = {
            row.payment_type: round(row.count / total * 100, 2) if total > 0 else 0.0
            for row in results
        }
        return {"overall_distribution": distribution, "total_trips": total}
    finally:
        db.close()


@router.get("/zones/tipping-score")
@cache(expire=3600)
def ranking_tipping_score(limit: int = Query(10, ge=1, le=100)):
    """UC13 — Ranking de zonas por Tipping Score (só viagens com cartão)"""
    db = SessionLocal()
    try:
        results = db.query(
            Trip.pickup_zone_id,
            func.avg(Trip.tip_amount / Trip.fare_amount * 100).label("score"),
        ).filter(
            Trip.fare_amount > 0,
            Trip.payment_type == "card",
        ).group_by(Trip.pickup_zone_id).order_by(
            func.avg(Trip.tip_amount / Trip.fare_amount * 100).desc()
        ).limit(limit).all()

        return [
            {"zone_id": row.pickup_zone_id, "score": round(row.score or 0.0, 2)}
            for row in results
        ]
    finally:
        db.close()


@router.get("/tips/passenger-correlation")
@cache(expire=3600)
def passenger_tip_correlation(
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date:   str = Query(None, description="YYYY-MM-DD"),
):
    """UC14 — Correlação entre número de passageiros e gorjeta"""
    db = SessionLocal()
    try:
        query = db.query(
            Trip.passenger_count,
            Trip.tip_amount,
            Trip.fare_amount,
        ).filter(
            Trip.fare_amount > 0,
            Trip.payment_type == "card",
            Trip.passenger_count > 0,
        ).limit(2000)

        if start_date:
            query = query.filter(Trip.pickup_date >= start_date)
        if end_date:
            query = query.filter(Trip.pickup_date <= end_date)

        rows = query.all()

        if not rows:
            return {"message": "Sem dados suficientes para o período selecionado."}

        passengers = [r.passenger_count for r in rows]
        tips_pct   = [r.tip_amount / r.fare_amount * 100 for r in rows]

        n      = len(passengers)
        mean_x = sum(passengers) / n
        mean_y = sum(tips_pct) / n
        num    = sum((x - mean_x) * (y - mean_y) for x, y in zip(passengers, tips_pct))
        den    = math.sqrt(
            sum((x - mean_x) ** 2 for x in passengers) *
            sum((y - mean_y) ** 2 for y in tips_pct)
        )
        correlation = round(num / den, 4) if den != 0 else 0.0

        if abs(correlation) < 0.3:   classif = "Fraca"
        elif abs(correlation) < 0.7: classif = "Moderada"
        else:                        classif = "Forte"

        return {
            "analyzed_trips":          n,
            "correlation_coefficient": correlation,
            "description": f"Correlação {classif} {'Positiva' if correlation > 0 else 'Negativa'}.",
        }
    finally:
        db.close()
