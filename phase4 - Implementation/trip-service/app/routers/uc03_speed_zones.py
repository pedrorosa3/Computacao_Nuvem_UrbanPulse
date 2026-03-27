from fastapi import APIRouter, Query, HTTPException
from datetime import date
from app.database import execute_query

router = APIRouter()

# Speed classification thresholds (km/h) derived from historical NYC taxi data:
#   slow   < 15 km/h
#   normal  15 – 30 km/h
#   fast   > 30 km/h
#
# Trip distance is in miles → convert to km (* 1.60934)
# Trip duration is in minutes → convert to hours (/ 60)

MILES_TO_KM = 1.60934

SLOW_THRESHOLD   = 15.0   # km/h
FAST_THRESHOLD   = 30.0   # km/h


@router.get(
    "/trips/speed/zones",
    summary="UC03 — Average speed per zone and period",
    description=(
        "Returns the average travel speed (km/h) per pickup zone and time-of-day period, "
        "classified as slow / normal / fast based on historical NYC thresholds."
    ),
)
def get_speed_by_zone(
    start_date:     date = Query(None, description="Filter from this date (inclusive)"),
    end_date:       date = Query(None, description="Filter up to this date (inclusive)"),
    pickup_zone_id:  int = Query(None, description="Filter by a specific pickup zone ID"),
    period:          str = Query(None, description="Filter by period: peak | off_peak | night"),
    limit:           int = Query(20, ge=1, le=100, description="Max zones to return"),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    valid_periods = {"peak", "off_peak", "night", None}
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"period must be one of: peak, off_peak, night"
        )

    filters = [
        "trip_distance > 0",
        "trip_duration_min > 0",
        "trip_distance IS NOT NULL",
        "trip_duration_min IS NOT NULL",
        "pickup_zone_id IS NOT NULL",
    ]
    params = []

    if start_date:
        filters.append("DATE(tpep_pickup_datetime) >= %s")
        params.append(start_date)
    if end_date:
        filters.append("DATE(tpep_pickup_datetime) <= %s")
        params.append(end_date)
    if pickup_zone_id is not None:
        filters.append("pickup_zone_id = %s")
        params.append(pickup_zone_id)

    where = "WHERE " + " AND ".join(filters)

    # Period filter applied after CTE
    period_filter = ""
    if period == "peak":
        period_filter = "AND time_period = 'peak'"
    elif period == "off_peak":
        period_filter = "AND time_period = 'off_peak'"
    elif period == "night":
        period_filter = "AND time_period = 'night'"

    query = f"""
        WITH classified AS (
            SELECT
                pickup_zone_id,
                pickup_zone_name,
                -- speed in km/h
                (trip_distance * {MILES_TO_KM}) / (trip_duration_min / 60.0) AS speed_kmh,
                CASE
                    WHEN EXTRACT(HOUR FROM tpep_pickup_datetime) BETWEEN 7  AND 9  THEN 'peak'
                    WHEN EXTRACT(HOUR FROM tpep_pickup_datetime) BETWEEN 16 AND 19 THEN 'peak'
                    WHEN EXTRACT(HOUR FROM tpep_pickup_datetime) >= 22
                         OR EXTRACT(HOUR FROM tpep_pickup_datetime) < 6             THEN 'night'
                    ELSE 'off_peak'
                END AS time_period
            FROM trips
            {where}
        )
        SELECT
            pickup_zone_id                              AS zone_id,
            pickup_zone_name                            AS zone_name,
            time_period,
            COUNT(*)                                    AS trip_count,
            ROUND(AVG(speed_kmh)::numeric, 2)           AS avg_speed_kmh,
            ROUND(MIN(speed_kmh)::numeric, 2)           AS min_speed_kmh,
            ROUND(MAX(speed_kmh)::numeric, 2)           AS max_speed_kmh,
            CASE
                WHEN AVG(speed_kmh) < {SLOW_THRESHOLD}  THEN 'slow'
                WHEN AVG(speed_kmh) <= {FAST_THRESHOLD} THEN 'normal'
                ELSE 'fast'
            END                                         AS classification
        FROM classified
        WHERE speed_kmh > 0
          AND speed_kmh < 200   -- exclude physically impossible outliers
          {period_filter}
        GROUP BY pickup_zone_id, pickup_zone_name, time_period
        HAVING COUNT(*) >= 5    -- need at least 5 trips to be statistically meaningful
        ORDER BY avg_speed_kmh DESC
        LIMIT %s
    """
    params.append(limit)

    rows = execute_query(query, tuple(params))

    return {
        "filters": {
            "start_date":     str(start_date)    if start_date    else None,
            "end_date":       str(end_date)      if end_date      else None,
            "pickup_zone_id": pickup_zone_id,
            "period":         period,
        },
        "classification_thresholds_kmh": {
            "slow":   f"avg_speed < {SLOW_THRESHOLD}",
            "normal": f"{SLOW_THRESHOLD} ≤ avg_speed ≤ {FAST_THRESHOLD}",
            "fast":   f"avg_speed > {FAST_THRESHOLD}",
        },
        "total_results": len(rows),
        "zones": [
            {
                "zone_id":        row["zone_id"],
                "zone_name":      row["zone_name"],
                "time_period":    row["time_period"],
                "trip_count":     int(row["trip_count"]),
                "avg_speed_kmh":  float(row["avg_speed_kmh"]),
                "min_speed_kmh":  float(row["min_speed_kmh"]),
                "max_speed_kmh":  float(row["max_speed_kmh"]),
                "classification": row["classification"],
            }
            for row in rows
        ],
    }
