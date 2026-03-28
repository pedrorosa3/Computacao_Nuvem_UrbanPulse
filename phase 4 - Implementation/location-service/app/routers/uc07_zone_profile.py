import math
from fastapi import APIRouter, Path, Query, HTTPException
from datetime import date
from typing import Optional
from app.database import execute_query
from app.demand_client import fetch_zone_hourly_demand

router = APIRouter()


def _classify_volatility(volatility_index: float) -> str:
    if volatility_index < 0.5:
        return "low"
    elif volatility_index <= 1.5:
        return "medium"
    else:
        return "high"


def _classify_attractiveness(score: float) -> str:
    if score >= 66:
        return "high"
    elif score >= 33:
        return "medium"
    else:
        return "low"


def _compute_volatility_index(hourly_counts: dict) -> tuple[float, int]:
    """
    Calcula o volatility_index normalizado (1.0 = média da cidade)
    e a peak_hour a partir dos hourly_counts do Demand Service.
    Retorna (volatility_index, peak_hour).
    """
    counts = [hourly_counts.get(h, 0) for h in range(24)]
    mean = sum(counts) / 24
    if mean == 0:
        return 1.0, 0

    stdev = math.sqrt(sum((c - mean) ** 2 for c in counts) / 24)
    cv = stdev / mean

    # Normalizar: assumimos cv médio da cidade = 0.8 (baseline NYC taxis)
    CITY_AVG_CV = 0.8
    volatility_index = round(cv / CITY_AVG_CV, 2)

    peak_hour = max(range(24), key=lambda h: hourly_counts.get(h, 0))
    return volatility_index, peak_hour


@router.get("/locations/{zone_id}/profile")
def get_zone_profile(
    zone_id:    int            = Path(..., description="Zone ID"),
    start_date: Optional[date] = Query(None),
    end_date:   Optional[date] = Query(None),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    # ── Verificar se a zona existe ────────────────────────────────────────────
    zone_rows = execute_query(
        "SELECT location_id, zone_name, borough FROM zones WHERE location_id = %s",
        (zone_id,)
    )
    if not zone_rows:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")

    zone = zone_rows[0]

    # ── Filtros de data ───────────────────────────────────────────────────────
    filters, params = [], []
    if start_date:
        filters.append("pickup_date >= %s")
        params.append(start_date)
    if end_date:
        filters.append("pickup_date <= %s")
        params.append(end_date)

    where_zone   = "WHERE pickup_zone_id = %s" + ("AND " + " AND ".join(filters) if filters else "")
    where_global = ("WHERE " + " AND ".join(filters)) if filters else ""

    # ── Trip volume da zona ───────────────────────────────────────────────────
    zone_trips_rows = execute_query(
        f"SELECT COUNT(*) AS total FROM trips WHERE pickup_zone_id = %s" +
        (" AND " + " AND ".join(filters) if filters else ""),
        (zone_id, *params)
    )
    total_trips = zone_trips_rows[0]["total"] if zone_trips_rows else 0

    # ── Total global (para market share) ─────────────────────────────────────
    global_rows = execute_query(
        f"SELECT COUNT(*) AS total FROM trips {where_global}",
        tuple(params)
    )
    global_total = global_rows[0]["total"] if global_rows else 0
    market_share = round(total_trips * 100.0 / global_total, 2) if global_total else 0.0

    # ── Financials ────────────────────────────────────────────────────────────
    fin_rows = execute_query(
        f"""
        SELECT
            ROUND(AVG(fare_amount)::NUMERIC, 2) AS avg_fare,
            ROUND(AVG(tip_amount)::NUMERIC, 2)  AS avg_tip
        FROM trips
        WHERE pickup_zone_id = %s
        """ + (" AND " + " AND ".join(filters) if filters else ""),
        (zone_id, *params)
    )
    avg_fare = float(fin_rows[0]["avg_fare"]) if fin_rows and fin_rows[0]["avg_fare"] else 0.0
    avg_tip  = float(fin_rows[0]["avg_tip"])  if fin_rows and fin_rows[0]["avg_tip"]  else 0.0
    avg_tip_pct = round(avg_tip / avg_fare * 100, 2) if avg_fare else 0.0

    # ── Demand patterns via gRPC ──────────────────────────────────────────────
    hourly_counts = fetch_zone_hourly_demand(zone_id)
    demand_patterns = None

    if hourly_counts is not None:
        volatility_index, peak_hour = _compute_volatility_index(hourly_counts)
        volatility_classification   = _classify_volatility(volatility_index)
        demand_patterns = {
            "peak_hour":               peak_hour,
            "peak_day":                None,   # TODO: disponível quando Demand Service expuser endpoint
            "volatility_index":        volatility_index,
            "volatility_classification": volatility_classification,
        }

    # ── Attractiveness score ──────────────────────────────────────────────────
    # Normalização simples: trip_volume (40%), avg_tip (35%), peak demand (25%)
    MAX_TRIPS = 500    # referência para normalização com 10k viagens de teste
    MAX_TIP   = 10.0   # referência para gorjeta máxima esperada

    score_volume = min(total_trips / MAX_TRIPS, 1.0) * 40
    score_tip    = min(avg_tip / MAX_TIP, 1.0) * 35
    score_demand = 0.0
    if demand_patterns:
        peak_intensity = hourly_counts.get(demand_patterns["peak_hour"], 0)
        score_demand = min(peak_intensity / (MAX_TRIPS / 24), 1.0) * 25

    attractiveness_score          = round(score_volume + score_tip + score_demand, 1)
    attractiveness_classification = _classify_attractiveness(attractiveness_score)

    return {
        "zone_id":   zone["location_id"],
        "zone_name": zone["zone_name"],
        "borough":   zone["borough"],
        "trip_volume": {
            "total_trips":      total_trips,
            "market_share_pct": market_share,
        },
        "financials": {
            "avg_fare":    avg_fare,
            "avg_tip":     avg_tip,
            "avg_tip_pct": avg_tip_pct,
        },
        "demand_patterns": demand_patterns,
        "attractiveness_score":          attractiveness_score,
        "attractiveness_classification": attractiveness_classification,
    }