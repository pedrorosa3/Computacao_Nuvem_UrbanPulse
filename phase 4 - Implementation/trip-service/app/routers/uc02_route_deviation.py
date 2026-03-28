from fastapi import APIRouter, Query, HTTPException
from datetime import date
from app.database import execute_query

router = APIRouter()


def safe_float(val):
    if val is None:
        return None
    f = float(val)
    return None if f != f else f


@router.get(
    "/trips/route-deviation",
    summary="UC02 — Route deviation index",
    description=(
        "Returns a summary of efficient / moderate / inefficient trip classifications "
        "based on the pre-computed deviation_index and deviation_class columns. "
        "Optionally filtered by date range and/or pickup zone."
    ),
)
def get_route_deviation(
    start_date:     date = Query(None, description="Filter from this date (inclusive)"),
    end_date:       date = Query(None, description="Filter up to this date (inclusive)"),
    pickup_zone_id:  int = Query(None, description="Filter by pickup zone ID"),
    limit:           int = Query(20, ge=1, le=100, description="Max individual trips to return"),
    summary_only:   bool = Query(False, description="Return only summary counts"),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    filters = ["deviation_class IS NOT NULL"]
    params  = []

    if start_date:
        filters.append("DATE(pickup_datetime) >= %s")
        params.append(start_date)
    if end_date:
        filters.append("DATE(pickup_datetime) <= %s")
        params.append(end_date)
    if pickup_zone_id is not None:
        filters.append("pickup_zone_id = %s")
        params.append(pickup_zone_id)

    where = "WHERE " + " AND ".join(filters)

    summary_query = f"""
        WITH totals AS (SELECT COUNT(*) AS total FROM trips {where})
        SELECT
            deviation_class                                                          AS classification,
            COUNT(*)                                                                 AS trip_count,
            ROUND(AVG(deviation_index)::numeric, 4)                                  AS avg_rdi,
            ROUND((COUNT(*) * 100.0 / NULLIF(t.total, 0))::numeric, 2)              AS percentage,
            t.total                                                                  AS total_trips
        FROM trips
        {where}
        CROSS JOIN totals t
        GROUP BY deviation_class, t.total
        ORDER BY
            CASE deviation_class
                WHEN 'efficient'   THEN 1
                WHEN 'moderate'    THEN 2
                WHEN 'inefficient' THEN 3
            END
    """
    # params duplicados: uma vez para o CTE, outra para o SELECT principal
    summary_rows = execute_query(summary_query, tuple(params) + tuple(params))
    total = int(summary_rows[0]["total_trips"]) if summary_rows else 0

    result = {
        "filters": {
            "start_date":     str(start_date)    if start_date    else None,
            "end_date":       str(end_date)      if end_date      else None,
            "pickup_zone_id": pickup_zone_id,
        },
        "classification_thresholds": {
            "efficient":   "RDI <= 1.20",
            "moderate":    "1.20 < RDI <= 1.60",
            "inefficient": "RDI > 1.60",
        },
        "total_trips_analysed": total,
        "summary": [
            {
                "classification": row["classification"],
                "trip_count":     int(row["trip_count"]),
                "avg_rdi":        safe_float(row["avg_rdi"]) or 0.0,
                "percentage":     safe_float(row["percentage"]) or 0.0,
            }
            for row in summary_rows
        ],
    }

    if summary_only:
        return result

    trips_query = f"""
        SELECT
            id,
            pickup_zone_id,
            pickup_zone_name,
            dropoff_zone_id,
            dropoff_zone_name,
            trip_distance_km,
            deviation_index,
            deviation_class
        FROM trips
        {where}
        ORDER BY deviation_index DESC
        LIMIT %s
    """
    # params uma só vez + limit
    trip_rows = execute_query(trips_query, tuple(params) + (limit,))

    result["sample_trips"] = [
        {
            "trip_id":           row["id"],
            "pickup_zone_id":    row["pickup_zone_id"],
            "pickup_zone_name":  row["pickup_zone_name"],
            "dropoff_zone_id":   row["dropoff_zone_id"],
            "dropoff_zone_name": row["dropoff_zone_name"],
            "trip_distance_km":  safe_float(row["trip_distance_km"]) or 0.0,
            "deviation_index":   safe_float(row["deviation_index"]) or 0.0,
            "classification":    row["deviation_class"],
        }
        for row in trip_rows
    ]

    return result