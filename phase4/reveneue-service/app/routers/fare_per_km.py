from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.db.connection import get_conn

router = APIRouter()

KM_PER_MILE = 1.60934


@router.get("/fare-per-km", summary="UC10 – Fare per km by zone")
def fare_per_km(
    zone_type: str           = Query("pickup", enum=["pickup", "dropoff"]),
    year:      Optional[int] = Query(None, example=2015),
    month:     Optional[int] = Query(None, ge=1, le=12, example=6),
    sort:      str           = Query("desc", enum=["asc", "desc"]),
    limit:     int           = Query(20, ge=1, le=263),
):
    zone_col = "pickup_zone_id" if zone_type == "pickup" else "dropoff_zone_id"

    conditions = [
        f"t.{zone_col} IS NOT NULL",
        "t.fare_amount > 0",
        "t.trip_distance_miles > 0.1",   # exclude near-zero distance trips
    ]
    params: list = []
    if year:
        conditions.append("EXTRACT(YEAR FROM t.pickup_datetime) = %s")
        params.append(year)
    if month:
        conditions.append("EXTRACT(MONTH FROM t.pickup_datetime) = %s")
        params.append(month)
    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            z.zone_id,
            z.zone_name,
            ROUND((AVG(t.fare_amount) / (AVG(t.trip_distance_miles) * {KM_PER_MILE}))::NUMERIC, 2)
                                                                    AS avg_fare_per_km,
            ROUND((AVG(t.trip_distance_miles) * {KM_PER_MILE})::NUMERIC, 2)
                                                                    AS avg_trip_distance_km,
            ROUND(AVG(t.fare_amount)::NUMERIC, 2)                   AS avg_fare,
            COUNT(*)                                                AS trip_count
        FROM trips t
        JOIN taxi_zones z ON z.zone_id = t.{zone_col}
        {where}
        GROUP BY z.zone_id, z.zone_name
        ORDER BY avg_fare_per_km {sort.upper()}
        LIMIT %s
    """
    params.append(limit)

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "filters_applied": {
            "zone_type": zone_type,
            "year":      year,
            "month":     month,
            "sort":      sort,
            "limit":     limit,
        },
        "zones": [
            {
                "zone_id":              r["zone_id"],
                "zone_name":            r["zone_name"],
                "avg_fare_per_km":      float(r["avg_fare_per_km"]),
                "avg_trip_distance_km": float(r["avg_trip_distance_km"]),
                "avg_fare":             float(r["avg_fare"]),
                "trip_count":           r["trip_count"],
            }
            for r in rows
        ],
    }
