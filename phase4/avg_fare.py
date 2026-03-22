from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.db.connection import get_conn

router = APIRouter()


@router.get("/avg-fare-by-zone", summary="UC08 – Average fare per zone with deviation from global average")
def avg_fare_by_zone(
    zone_type: str = Query("pickup", enum=["pickup", "dropoff"]),
    year:      Optional[int] = Query(None, example=2015),
    month:     Optional[int] = Query(None, ge=1, le=12, example=6),
    sort:      str           = Query("desc", enum=["asc", "desc"]),
    limit:     int           = Query(20, ge=1, le=263),
):
    zone_col = "pickup_zone_id" if zone_type == "pickup" else "dropoff_zone_id"

    # Build WHERE clause
    conditions = [f"t.{zone_col} IS NOT NULL", "t.fare_amount > 0"]
    params: list = []
    if year:
        conditions.append("EXTRACT(YEAR FROM t.pickup_datetime) = %s")
        params.append(year)
    if month:
        conditions.append("EXTRACT(MONTH FROM t.pickup_datetime) = %s")
        params.append(month)
    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        WITH zone_stats AS (
            SELECT
                z.zone_id,
                z.zone_name,
                AVG(t.fare_amount)  AS avg_fare,
                COUNT(*)            AS trip_count
            FROM trips t
            JOIN taxi_zones z ON z.zone_id = t.{zone_col}
            {where}
            GROUP BY z.zone_id, z.zone_name
        ),
        global_avg AS (
            SELECT AVG(fare_amount) AS global_avg_fare
            FROM trips t
            {where}
        )
        SELECT
            zs.zone_id,
            zs.zone_name,
            ROUND(zs.avg_fare::NUMERIC, 2)                                          AS avg_fare,
            ROUND((zs.avg_fare - ga.global_avg_fare)::NUMERIC, 2)                   AS deviation_absolute,
            ROUND(((zs.avg_fare - ga.global_avg_fare) / ga.global_avg_fare * 100)::NUMERIC, 2) AS deviation_percentage,
            zs.trip_count,
            ROUND(ga.global_avg_fare::NUMERIC, 2)                                   AS global_avg_fare
        FROM zone_stats zs, global_avg ga
        ORDER BY avg_fare {sort.upper()}
        LIMIT %s
    """
    params_with_limit = params + params + [limit]

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params_with_limit)
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not rows:
        return {
            "filters_applied": {"zone_type": zone_type, "year": year, "month": month, "sort": sort, "limit": limit},
            "global_avg_fare": None,
            "zones": [],
        }

    global_avg_fare = float(rows[0]["global_avg_fare"])
    zones = [
        {
            "zone_id":            r["zone_id"],
            "zone_name":          r["zone_name"],
            "avg_fare":           float(r["avg_fare"]),
            "deviation_absolute": float(r["deviation_absolute"]),
            "deviation_percentage": float(r["deviation_percentage"]),
            "trip_count":         r["trip_count"],
        }
        for r in rows
    ]

    return {
        "filters_applied": {
            "zone_type": zone_type,
            "year":      year,
            "month":     month,
            "sort":      sort,
            "limit":     limit,
        },
        "global_avg_fare": global_avg_fare,
        "zones":           zones,
    }
