from fastapi import APIRouter, Path, Query, HTTPException
from datetime import date
from app.database import execute_query

router = APIRouter()

@router.get("/locations/{zone_id}/dropoffs")
def get_top_dropoffs(
    zone_id:    int  = Path(..., description="Pickup zone ID"),
    limit:      int  = Query(10, ge=1, le=50),
    start_date: date = Query(None),
    end_date:   date = Query(None),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    # Verificar se a zona existe
    zone_rows = execute_query(
        "SELECT location_id, zone_name, borough FROM zones WHERE location_id = %s",
        (zone_id,)
    )
    if not zone_rows:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")

    zone = zone_rows[0]

    # Filtros de data
    filters = ["t.pickup_zone_id = %s"]
    params  = [zone_id]
    if start_date:
        filters.append("t.pickup_date >= %s")
        params.append(start_date)
    if end_date:
        filters.append("t.pickup_date <= %s")
        params.append(end_date)

    where = "WHERE " + " AND ".join(filters)

    # Total de viagens da zona de origem
    total_rows = execute_query(
        f"SELECT COUNT(*) AS total FROM trips t {where}",
        tuple(params)
    )
    total_from_zone = total_rows[0]["total"]

    # Top dropoffs
    query = f"""
        WITH dropoff_counts AS (
            SELECT
                t.dropoff_zone_id,
                t.dropoff_zone_name,
                COUNT(*) AS trip_count
            FROM trips t
            {where}
            GROUP BY t.dropoff_zone_id, t.dropoff_zone_name
        )
        SELECT
            ROW_NUMBER() OVER (ORDER BY dc.trip_count DESC) AS rank,
            dc.dropoff_zone_id                              AS zone_id,
            dc.dropoff_zone_name                            AS zone_name,
            z.borough,
            dc.trip_count,
            ROUND((dc.trip_count * 100.0 / %s)::numeric, 2) AS destination_share_pct
        FROM dropoff_counts dc
        JOIN zones z ON z.location_id = dc.dropoff_zone_id
        ORDER BY dc.trip_count DESC
        LIMIT %s
    """
    params_dropoff = tuple(params) + (total_from_zone, limit)
    rows = execute_query(query, params_dropoff)

    return {
        "origin_zone": {
            "zone_id":             zone["location_id"],
            "zone_name":           zone["zone_name"],
            "borough":             zone["borough"],
            "total_trips_from_zone": total_from_zone,
        },
        "dropoffs": [
            {
                "rank":                  int(row["rank"]),
                "zone_id":               row["zone_id"],
                "zone_name":             row["zone_name"],
                "borough":               row["borough"],
                "trip_count":            row["trip_count"],
                "destination_share_pct": float(row["destination_share_pct"]),
            }
            for row in rows
        ],
    }
