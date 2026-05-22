import math
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.db.connection import get_conn
from app.grpc_client import fetch_zone_info  # <--- IMPORT NOVO!

router = APIRouter()

@router.get("/zone-volatility", summary="UC17 – Zone demand volatility over the day")
def zone_volatility(
    zone_id: int = Query(..., example=161, description="ID da zona a analisar"),
    year: Optional[int] = Query(None, example=2015),
    month: Optional[int] = Query(None, ge=1, le=12, example=1),
):
    """
    Analisa a instabilidade (volatilidade) da procura numa zona específica ao longo das 24 horas.
    Utiliza o Coeficiente de Variação (CV) = Desvio Padrão / Média.
    """
    
    # 1. Preparar a query SQL e os filtros
    conditions = ["pickup_zone_id = %s"]
    params: list = [zone_id]
    
    if year:
        conditions.append("pickup_year = %s")
        params.append(year)
    if month:
        conditions.append("pickup_month = %s")
        params.append(month)

    where = "WHERE " + " AND ".join(conditions)

    # Vamos agrupar as viagens por hora do dia e contar quantas há
    query = f"""
        SELECT
            pickup_hour AS hour,
            COUNT(*)    AS trip_count
        FROM trips
        {where}
        GROUP BY pickup_hour
        ORDER BY pickup_hour
    """

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not rows:
         return {
            "zone_id": zone_id,
            "status": "No data",
            "message": "Não existem viagens registadas para esta zona com os filtros aplicados."
        }

    # 2. Processar os dados
    # Mapear os resultados para um dicionário, garantindo que as horas sem viagens ficam a 0
    cell_map = {int(r["hour"]): int(r["trip_count"]) for r in rows}
    
    hourly_counts = []
    for h in range(24):
        hourly_counts.append(cell_map.get(h, 0))

    # 3. Matemática da Volatilidade
    n = len(hourly_counts) # Será sempre 24
    mean_demand = sum(hourly_counts) / n
    
    if mean_demand == 0:
         return {"zone_id": zone_id, "status": "Inactive", "message": "Zona sem atividade."}

    # Desvio Padrão Populacional
    sum_sq_diff = sum((x - mean_demand) ** 2 for x in hourly_counts)
    stdev = math.sqrt(sum_sq_diff / n)
    
    # Coeficiente de Variação (CV)
    cv = stdev / mean_demand
    
    # 4. Classificar a Instabilidade
    if cv < 0.5:
        classification = "Stable"
    elif cv < 1.0:
        classification = "Moderate Volatility"
    else:
        classification = "Highly Unstable (Extreme Peaks)"

    # ... (todo o código SQL e cálculo matemático que fizemos antes fica igual) ...

    # Identificar as horas de pico
    peak_threshold = mean_demand + stdev
    peak_hours = [h for h, count in enumerate(hourly_counts) if count > peak_threshold]

    # --- MAGIA DO MICROSERVIÇO: Pedir dados ao Location Service ---
    zone_info = fetch_zone_info(zone_id)
    
    if zone_info:
        zone_details = f"{zone_info['borough']} - {zone_info['zone_name']}"
    else:
        zone_details = "Desconhecida (A aguardar Location Service)"

    # --- RESPOSTA ATUALIZADA ---
    return {
        "zone_id": zone_id,
        "zone_name": zone_details, # <--- DADO VINDO POR gRPC!
        "filters_applied": {"year": year, "month": month},
        "volatility_metrics": {
            "average_trips_per_hour": round(mean_demand, 2),
            "standard_deviation": round(stdev, 2),
            "coefficient_of_variation": round(cv, 4),
            "classification": classification
        },
        "peak_analysis": {
            "peak_threshold": round(peak_threshold, 2),
            "identified_peak_hours": peak_hours
        },
        "hourly_distribution": {f"{h:02d}:00": count for h, count in enumerate(hourly_counts)}
    }