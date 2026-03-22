from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.db.connection import get_conn

router = APIRouter()


@router.get("/breakdown", summary="UC09 – Percentage breakdown of trip revenue")
def revenue_breakdown(
    zone_id:   Optional[int] = Query(None, example=161),
    zone_type: str           = Query("pickup", enum=["pickup", "dropoff"]),
    year:      Optional[int] = Query(None, example=2015),
    month:     Optional[int] = Query(None, ge=1, le=12, example=6),
):
    zone_col = "pickup_zone_id" if zone_type == "pickup" else "dropoff_zone_id"

    conditions = ["total_amount > 0", "fare_amount > 0"]
    params: list = []
    if zone_id is not None:
        conditions.append(f"{zone_col} = %s")
        params.append(zone_id)
    if year:
        conditions.append("EXTRACT(YEAR FROM pickup_datetime) = %s")
        params.append(year)
    if month:
        conditions.append("EXTRACT(MONTH FROM pickup_datetime) = %s")
        params.append(month)
    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            COUNT(*)                        AS trip_count,
            ROUND(AVG(total_amount)::NUMERIC, 4)            AS avg_total,
            ROUND(AVG(fare_amount)::NUMERIC, 4)             AS avg_fare,
            ROUND(AVG(tip_amount)::NUMERIC, 4)              AS avg_tip,
            ROUND(AVG(tolls_amount)::NUMERIC, 4)            AS avg_tolls,
            ROUND(AVG(mta_tax)::NUMERIC, 4)                 AS avg_mta,
            ROUND(AVG(improvement_surcharge)::NUMERIC, 4)   AS avg_surcharge,
            ROUND(AVG(extra)::NUMERIC, 4)                   AS avg_extra
        FROM trips
        {where}
    """

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not row or row["trip_count"] == 0:
        raise HTTPException(status_code=404, detail="No trips found for the given filters.")

    avg_total   = float(row["avg_total"])
    avg_fare    = float(row["avg_fare"])
    avg_tip     = float(row["avg_tip"])
    avg_tolls   = float(row["avg_tolls"])
    avg_mta     = float(row["avg_mta"])
    avg_sur     = float(row["avg_surcharge"])
    avg_extra   = float(row["avg_extra"])

    def pct(val: float) -> float:
        return round(val / avg_total * 100, 2) if avg_total else 0.0

    return {
        "filters_applied": {
            "zone_id":   zone_id,
            "zone_type": zone_type,
            "year":      year,
            "month":     month,
        },
        "trip_count":       int(row["trip_count"]),
        "avg_total_amount": round(avg_total, 2),
        "breakdown": {
            "fare_amount":           {"avg": round(avg_fare,  2), "percentage": pct(avg_fare)},
            "tip_amount":            {"avg": round(avg_tip,   2), "percentage": pct(avg_tip)},
            "tolls_amount":          {"avg": round(avg_tolls, 2), "percentage": pct(avg_tolls)},
            "mta_tax":               {"avg": round(avg_mta,   2), "percentage": pct(avg_mta)},
            "improvement_surcharge": {"avg": round(avg_sur,   2), "percentage": pct(avg_sur)},
            "extra":                 {"avg": round(avg_extra, 2), "percentage": pct(avg_extra)},
        },
    }
