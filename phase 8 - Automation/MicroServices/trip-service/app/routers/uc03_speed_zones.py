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
    "/trips/speed/zones",
    summary="UC03 — Average speed per zone and period",
    description=(
        "Returns average travel speed (km/h) per pickup zone and time-of-day period, "
        "using the pre-computed avg_speed_kmh and speed_class columns."
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
        raise HTTPException(status_code=400, detail="period must be one of: peak, off_peak, night")

    filters = ["avg_speed_kmh IS NOT NULL", "pickup_zone_id IS NOT NULL"]
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
    if period is not None:
        filters.append("time_class = %s")
        params.append(period)

    where = "WHERE " + " AND ".join(filters)

    query = f"""
        SELECT
            pickup_zone_id                              AS zone_id,
            pickup_zone_name                            AS zone_name,
            time_class                                  AS time_period,
            COUNT(*)                                    AS trip_count,
            ROUND(AVG(avg_speed_kmh)::numeric, 2)       AS avg_speed_kmh,
            ROUND(MIN(avg_speed_kmh)::numeric, 2)       AS min_speed_kmh,
            ROUND(MAX(avg_speed_kmh)::numeric, 2)       AS max_speed_kmh,
            MODE() WITHIN GROUP (ORDER BY speed_class)  AS classification
        FROM trips
        {where}
        GROUP BY pickup_zone_id, pickup_zone_name, time_class
        HAVING COUNT(*) >= 5
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
            "slow":   "avg_speed < 15",
            "normal": "15 <= avg_speed <= 30",
            "fast":   "avg_speed > 30",
        },
        "total_results": len(rows),
        "zones": [
            {
                "zone_id":        row["zone_id"],
                "zone_name":      row["zone_name"] or "",
                "time_period":    row["time_period"] or "",
                "trip_count":     int(row["trip_count"]),
                "avg_speed_kmh":  safe_float(row["avg_speed_kmh"]),
                "min_speed_kmh":  safe_float(row["min_speed_kmh"]),
                "max_speed_kmh":  safe_float(row["max_speed_kmh"]),
                "classification": row["classification"] or None,
            }
            for row in rows
        ],
    }