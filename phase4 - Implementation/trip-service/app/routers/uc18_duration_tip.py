from fastapi import APIRouter, Query, HTTPException
from datetime import date
from app.database import execute_query

router = APIRouter()



@router.get(
    "/trips/duration-tip-correlation",
    summary="UC18 — Duration vs tip correlation",
    description=(
        "Analyses whether longer trips tend to receive higher tips. "
        "Returns Pearson correlation coefficient, average tip per duration bucket, "
        "and tip-to-fare ratio per bucket. Only credit card trips are included "
        "(cash tips are not recorded in the dataset)."
    ),
)
def get_duration_tip_correlation(
    start_date:     date = Query(None, description="Filter from this date (inclusive)"),
    end_date:       date = Query(None, description="Filter up to this date (inclusive)"),
    pickup_zone_id:  int = Query(None, description="Filter by pickup zone ID"),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    filters = [
        "tip_amount >= 0",
        "fare_amount > 0",
        "trip_duration_min > 0",
        "trip_duration_min IS NOT NULL",
        "tip_amount IS NOT NULL",
        "payment_type = 1",   # Credit card — cash tips not recorded
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

    # Pearson correlation
    corr_query = f"""
        SELECT
            ROUND(CORR(trip_duration_min, tip_amount)::numeric, 4) AS pearson_correlation,
            COUNT(*)                                                AS total_trips,
            ROUND(AVG(tip_amount)::numeric, 2)                     AS avg_tip,
            ROUND(AVG(trip_duration_min)::numeric, 2)              AS avg_duration_min
        FROM trips
        {where}
    """
    corr_rows = execute_query(corr_query, tuple(params))
    corr = corr_rows[0] if corr_rows else {}

    # Bucket analysis
    bucket_query = f"""
        SELECT
            CASE
                WHEN trip_duration_min < 10               THEN '0-10 min'
                WHEN trip_duration_min < 20               THEN '10-20 min'
                WHEN trip_duration_min < 30               THEN '20-30 min'
                WHEN trip_duration_min < 60               THEN '30-60 min'
                ELSE                                           '60+ min'
            END                                                AS duration_bucket,
            CASE
                WHEN trip_duration_min < 10  THEN 1
                WHEN trip_duration_min < 20  THEN 2
                WHEN trip_duration_min < 30  THEN 3
                WHEN trip_duration_min < 60  THEN 4
                ELSE                              5
            END                                                AS bucket_order,
            COUNT(*)                                           AS trip_count,
            ROUND(AVG(tip_amount)::numeric, 2)                 AS avg_tip,
            ROUND(AVG(tip_amount / NULLIF(fare_amount, 0) * 100)::numeric, 2) AS avg_tip_rate_pct,
            ROUND(MIN(tip_amount)::numeric, 2)                 AS min_tip,
            ROUND(MAX(tip_amount)::numeric, 2)                 AS max_tip
        FROM trips
        {where}
        GROUP BY duration_bucket, bucket_order
        ORDER BY bucket_order
    """
    bucket_rows = execute_query(bucket_query, tuple(params))

    # Interpret correlation strength
    pearson = float(corr.get("pearson_correlation") or 0)
    if abs(pearson) < 0.1:
        strength = "negligible"
    elif abs(pearson) < 0.3:
        strength = "weak"
    elif abs(pearson) < 0.5:
        strength = "moderate"
    elif abs(pearson) < 0.7:
        strength = "strong"
    else:
        strength = "very strong"

    direction = "positive" if pearson >= 0 else "negative"

    return {
        "filters": {
            "start_date":     str(start_date)    if start_date    else None,
            "end_date":       str(end_date)      if end_date      else None,
            "pickup_zone_id": pickup_zone_id,
        },
        "note": "Only credit card trips included (payment_type=1); cash tips are not recorded.",
        "total_trips_analysed": int(corr.get("total_trips") or 0),
        "avg_duration_min":     float(corr.get("avg_duration_min") or 0),
        "avg_tip":              float(corr.get("avg_tip") or 0),
        "pearson_correlation":  pearson,
        "correlation_strength": strength,
        "correlation_direction": direction,
        "interpretation": (
            f"There is a {strength} {direction} correlation between trip duration and tip amount."
        ),
        "duration_buckets": [
            {
                "duration_bucket":  row["duration_bucket"],
                "trip_count":       int(row["trip_count"]),
                "avg_tip":          float(row["avg_tip"]),
                "avg_tip_rate_pct": float(row["avg_tip_rate_pct"]) if row["avg_tip_rate_pct"] else None,
                "min_tip":          float(row["min_tip"]),
                "max_tip":          float(row["max_tip"]),
            }
            for row in bucket_rows
        ],
    }
