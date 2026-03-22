from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.db.connection import get_conn

router = APIRouter()

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Peak hour threshold: cells with trip_count > overall_avg * PEAK_FACTOR are flagged
PEAK_FACTOR = 1.25


@router.get("/hourly-matrix", summary="UC15 – Trip count matrix by hour and day of week")
def hourly_matrix(
    zone_id: Optional[int] = Query(None, example=161),
    year:    Optional[int] = Query(None, example=2015),
    month:   Optional[int] = Query(None, ge=1, le=12, example=6),
):
    conditions = ["pickup_datetime IS NOT NULL"]
    params: list = []
    if zone_id is not None:
        conditions.append("pickup_zone_id = %s")
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
            -- PostgreSQL DOW: 0=Sunday … 6=Saturday  →  convert to 0=Monday … 6=Sunday
            CASE (EXTRACT(DOW FROM pickup_datetime)::INT)
                WHEN 0 THEN 6
                ELSE EXTRACT(DOW FROM pickup_datetime)::INT - 1
            END AS day_of_week,
            EXTRACT(HOUR FROM pickup_datetime)::INT AS hour,
            COUNT(*) AS trip_count
        FROM trips
        {where}
        GROUP BY day_of_week, hour
        ORDER BY day_of_week, hour
    """

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Build lookup: (day, hour) -> count
    cell_map: dict[tuple, int] = {
        (int(r["day_of_week"]), int(r["hour"])): int(r["trip_count"])
        for r in rows
    }

    total_cells = 7 * 24
    total_trips = sum(cell_map.values())
    overall_avg = total_trips / total_cells if total_cells > 0 else 0
    peak_threshold = overall_avg * PEAK_FACTOR

    matrix = []
    for dow in range(7):
        hours_data = []
        for h in range(24):
            count = cell_map.get((dow, h), 0)
            hours_data.append({
                "hour":       h,
                "trip_count": count,
                "is_peak":    count >= peak_threshold,
            })
        matrix.append({
            "day_of_week": dow,
            "day_name":    DAY_NAMES[dow],
            "hours":       hours_data,
        })

    return {
        "filters_applied": {
            "zone_id": zone_id,
            "year":    year,
            "month":   month,
        },
        "overall_avg_trips": round(overall_avg, 2),
        "matrix": matrix,
    }
