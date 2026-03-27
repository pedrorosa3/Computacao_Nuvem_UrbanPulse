from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.db.connection import get_conn

router = APIRouter()


@router.get("/avg-fare-by-zone", summary="UC08 – Average fare per zone with deviation from global average")
def avg_fare_by_zone(
    zone_type:  str           = Query("pickup", enum=["pickup", "dropoff"]),
    zone_id:    Optional[int] = Query(None, example=161),
    start_date: Optional[str] = Query(None, example="2015-01-01"),
    end_date:   Optional[str] = Query(None, example="2015-12-31"),
    sort:       str           = Query("desc", enum=["asc", "desc"]),
    limit:      int           = Query(20, ge=1, le=263),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    zone_col = "pickup_zone_id" if zone_type == "pickup" else "dropoff_zone_id"

    conditions = ["fare_amount > 0"]
    params: list = []
    if zone_id is not None:
        conditions.append(f"{zone_col} = %s")
        params.append(zone_id)
    if start_date:
        conditions.append("pickup_date >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("pickup_date <= %s")
        params.append(end_date)

    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        WITH zone_stats AS (
            SELECT
                {zone_col}              AS zone_id,
                AVG(fare_amount)        AS avg_fare,
                COUNT(*)                AS trip_count
            FROM trips
            {where}
            GROUP BY {zone_col}
        ),
        global_avg AS (
            SELECT AVG(fare_amount) AS global_avg_fare
            FROM trips
            {where}
        )
        SELECT
            zs.zone_id,
            ROUND(zs.avg_fare::NUMERIC, 2)                                                     AS avg_fare,
            ROUND((zs.avg_fare - ga.global_avg_fare)::NUMERIC, 2)                              AS deviation_absolute,
            ROUND(((zs.avg_fare - ga.global_avg_fare) / ga.global_avg_fare * 100)::NUMERIC, 2) AS deviation_percentage,
            zs.trip_count,
            ROUND(ga.global_avg_fare::NUMERIC, 2)                                              AS global_avg_fare
        FROM zone_stats zs, global_avg ga
        ORDER BY avg_fare {sort.upper()}
        LIMIT %s
    """
    params_query = params + params + [limit]

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params_query)
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not rows:
        return {
            "filters_applied": {
                "zone_type": zone_type, "zone_id": zone_id,
                "start_date": start_date, "end_date": end_date,
                "sort": sort, "limit": limit,
            },
            "global_avg_fare": None,
            "zones": [],
        }

    global_avg_fare = float(rows[0]["global_avg_fare"])

    return {
        "filters_applied": {
            "zone_type":  zone_type,
            "zone_id":    zone_id,
            "start_date": start_date,
            "end_date":   end_date,
            "sort":       sort,
            "limit":      limit,
        },
        "global_avg_fare": global_avg_fare,
        "zones": [
            {
                "zone_id":              r["zone_id"],
                "zone_name":            None,   # TODO: enriquecer via Location Service (gRPC)
                "avg_fare":             float(r["avg_fare"]),
                "deviation_absolute":   float(r["deviation_absolute"]),
                "deviation_percentage": float(r["deviation_percentage"]),
                "trip_count":           r["trip_count"],
            }
            for r in rows
        ],
    }