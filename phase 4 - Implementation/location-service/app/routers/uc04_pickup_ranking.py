from fastapi import APIRouter, Query, HTTPException
from datetime import date
from app.database import execute_query

router = APIRouter()

@router.get("/locations/pickup/ranking")
def get_pickup_zone_ranking(
    start_date: date = Query(None),
    end_date:   date = Query(None),
    limit:      int  = Query(10, ge=1, le=50),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    # Filtros de data
    filters = []
    params  = []
    if start_date:
        filters.append("t.pickup_date >= %s")
        params.append(start_date)
    if end_date:
        filters.append("t.pickup_date <= %s")
        params.append(end_date)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    query = f"""
        WITH zone_counts AS (
            SELECT
                t.pickup_zone_id,
                t.pickup_zone_name,
                COUNT(*) AS trip_count
            FROM trips t
            {where}
            GROUP BY t.pickup_zone_id, t.pickup_zone_name
        ),
        total AS (
            SELECT SUM(trip_count) AS total_trips FROM zone_counts
        )
        SELECT
            ROW_NUMBER() OVER (ORDER BY zc.trip_count DESC) AS rank,
            zc.pickup_zone_id                               AS zone_id,
            zc.pickup_zone_name                             AS zone_name,
            z.borough,
            zc.trip_count,
            ROUND((zc.trip_count * 100.0 / t.total_trips)::numeric, 2) AS market_share_pct
        FROM zone_counts zc
        JOIN zones z ON z.location_id = zc.pickup_zone_id
        CROSS JOIN total t
        ORDER BY zc.trip_count DESC
        LIMIT %s
    """
    params.append(limit)

    rows = execute_query(query, tuple(params))

    # Total de viagens no período
    total_query = f"SELECT COUNT(*) AS total FROM trips t {where}"
    total = execute_query(total_query, tuple(params[:-1]))[0]["total"]

    return {
        "period": {
            "start_date": str(start_date) if start_date else None,
            "end_date":   str(end_date)   if end_date   else None,
        },
        "total_trips": total,
        "zones": [
            {
                "rank":             int(row["rank"]),
                "zone_id":          row["zone_id"],
                "zone_name":        row["zone_name"],
                "borough":          row["borough"],
                "trip_count":       row["trip_count"],
                "market_share_pct": float(row["market_share_pct"]),
            }
            for row in rows
        ],
    }
