from fastapi import APIRouter, Query, HTTPException
from datetime import date
from app.database import execute_query

router = APIRouter()

@router.get(
    "/trips/classification/time-of-day",
    summary="UC01 — Classify trips by time of day",
    description=(
        "Counts and percentages of trips grouped by time-of-day period "
        "(peak / off-peak / night), optionally filtered by date range and/or zone."
    ),
)
def classify_trips_by_time_of_day(
    start_date:    date = Query(None, description="Filter from this date (inclusive)"),
    end_date:      date = Query(None, description="Filter up to this date (inclusive)"),
    pickup_zone_id: int = Query(None, description="Filter by pickup zone ID"),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    filters = []
    params  = []

    if start_date:
        filters.append("DATE(tpep_pickup_datetime) >= %s")
        params.append(start_date)
    if end_date:
        filters.append("DATE(tpep_pickup_datetime) <= %s")
        params.append(end_date)
    if pickup_zone_id is not None:
        filters.append("pickup_zone_id = %s")
        params.append(pickup_zone_id)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    query = f"""
        WITH classified AS (
            SELECT
                CASE
                    WHEN EXTRACT(HOUR FROM tpep_pickup_datetime) BETWEEN 7  AND 9  THEN 'peak'
                    WHEN EXTRACT(HOUR FROM tpep_pickup_datetime) BETWEEN 16 AND 19 THEN 'peak'
                    WHEN EXTRACT(HOUR FROM tpep_pickup_datetime) >= 22
                         OR EXTRACT(HOUR FROM tpep_pickup_datetime) < 6             THEN 'night'
                    ELSE 'off_peak'
                END AS period
            FROM trips
            {where}
        ),
        totals AS (
            SELECT COUNT(*) AS total FROM classified
        )
        SELECT
            c.period,
            COUNT(*)                                                     AS trip_count,
            ROUND((COUNT(*) * 100.0 / t.total)::numeric, 2)             AS percentage,
            t.total                                                      AS total_trips
        FROM classified c
        CROSS JOIN totals t
        GROUP BY c.period, t.total
        ORDER BY trip_count DESC
    """

    rows = execute_query(query, tuple(params))

    if not rows:
        return {
            "filters": {
                "start_date":    str(start_date)    if start_date    else None,
                "end_date":      str(end_date)      if end_date      else None,
                "pickup_zone_id": pickup_zone_id,
            },
            "total_trips": 0,
            "periods": [],
        }

    total = rows[0]["total_trips"]

    return {
        "filters": {
            "start_date":    str(start_date)    if start_date    else None,
            "end_date":      str(end_date)      if end_date      else None,
            "pickup_zone_id": pickup_zone_id,
        },
        "period_definitions": {
            "peak":     "07:00–09:59 and 16:00–19:59",
            "off_peak": "06:00–15:59 and 20:00–21:59",
            "night":    "22:00–05:59",
        },
        "total_trips": int(total),
        "periods": [
            {
                "period":     row["period"],
                "trip_count": int(row["trip_count"]),
                "percentage": float(row["percentage"]),
            }
            for row in rows
        ],
    }
