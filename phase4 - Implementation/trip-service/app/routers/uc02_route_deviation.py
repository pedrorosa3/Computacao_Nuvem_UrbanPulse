from fastapi import APIRouter, Query, HTTPException
from datetime import date
from app.database import execute_query

router = APIRouter()


REFERENCE_SPEED_MPH = 12.0


@router.get(
    "/trips/route-deviation",
    summary="UC02 — Route deviation index",
    description=(
        "Computes the Route Deviation Index (RDI) for each trip and returns "
        "a summary of efficient / moderate / inefficient classifications, "
        "optionally filtered by date range and/or pickup zone."
    ),
)
def get_route_deviation(
    start_date:     date = Query(None, description="Filter from this date (inclusive)"),
    end_date:       date = Query(None, description="Filter up to this date (inclusive)"),
    pickup_zone_id:  int = Query(None, description="Filter by pickup zone ID"),
    limit:           int = Query(20, ge=1, le=100, description="Max individual trip rows to return"),
    summary_only:   bool = Query(False, description="Return only the summary counts, not individual trips"),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    filters = [
        "trip_distance > 0",
        "trip_duration_min > 0",
        "trip_distance IS NOT NULL",
        "trip_duration_min IS NOT NULL",
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

    # Summary query
    summary_query = f"""
        WITH rdi AS (
            SELECT
                id,
                pickup_zone_id,
                pickup_zone_name,
                trip_distance,
                trip_duration_min,
                ROUND(
                    (trip_duration_min / ((trip_distance / {REFERENCE_SPEED_MPH}) * 60))::numeric,
                    4
                ) AS rdi_value,
                CASE
                    WHEN (trip_duration_min / ((trip_distance / {REFERENCE_SPEED_MPH}) * 60)) <= 1.20
                        THEN 'efficient'
                    WHEN (trip_duration_min / ((trip_distance / {REFERENCE_SPEED_MPH}) * 60)) <= 1.60
                        THEN 'moderate'
                    ELSE 'inefficient'
                END AS classification
            FROM trips
            {where}
        ),
        totals AS (SELECT COUNT(*) AS total FROM rdi)
        SELECT
            r.classification,
            COUNT(*)                                             AS trip_count,
            ROUND(AVG(r.rdi_value)::numeric, 4)                 AS avg_rdi,
            ROUND((COUNT(*) * 100.0 / t.total)::numeric, 2)     AS percentage,
            t.total                                              AS total_trips
        FROM rdi r
        CROSS JOIN totals t
        GROUP BY r.classification, t.total
        ORDER BY
            CASE r.classification
                WHEN 'efficient'    THEN 1
                WHEN 'moderate'     THEN 2
                WHEN 'inefficient'  THEN 3
            END
    """

    summary_rows = execute_query(summary_query, tuple(params))

    total = int(summary_rows[0]["total_trips"]) if summary_rows else 0

    result = {
        "filters": {
            "start_date":     str(start_date)    if start_date    else None,
            "end_date":       str(end_date)      if end_date      else None,
            "pickup_zone_id": pickup_zone_id,
        },
        "reference_speed_mph": REFERENCE_SPEED_MPH,
        "classification_thresholds": {
            "efficient":   "RDI ≤ 1.20 (actual ≤ 20% over direct-route time)",
            "moderate":    "1.20 < RDI ≤ 1.60",
            "inefficient": "RDI > 1.60 (actual > 60% over direct-route time)",
        },
        "total_trips_analysed": total,
        "summary": [
            {
                "classification": row["classification"],
                "trip_count":     int(row["trip_count"]),
                "avg_rdi":        float(row["avg_rdi"]),
                "percentage":     float(row["percentage"]),
            }
            for row in summary_rows
        ],
    }

    if summary_only:
        return result

    # Sample trips query (top N by highest RDI so the user sees the worst offenders)
    trips_query = f"""
        SELECT
            id,
            pickup_zone_id,
            pickup_zone_name,
            dropoff_zone_id,
            dropoff_zone_name,
            trip_distance,
            ROUND(trip_duration_min::numeric, 2)  AS trip_duration_min,
            ROUND(
                (trip_duration_min / ((trip_distance / {REFERENCE_SPEED_MPH}) * 60))::numeric,
                4
            )                                     AS rdi_value,
            CASE
                WHEN (trip_duration_min / ((trip_distance / {REFERENCE_SPEED_MPH}) * 60)) <= 1.20
                    THEN 'efficient'
                WHEN (trip_duration_min / ((trip_distance / {REFERENCE_SPEED_MPH}) * 60)) <= 1.60
                    THEN 'moderate'
                ELSE 'inefficient'
            END                                   AS classification
        FROM trips
        {where}
        ORDER BY rdi_value DESC
        LIMIT %s
    """
    trip_rows = execute_query(trips_query, tuple(params) + (limit,))

    result["sample_trips"] = [
        {
            "trip_id":            row["id"],
            "pickup_zone_id":     row["pickup_zone_id"],
            "pickup_zone_name":   row["pickup_zone_name"],
            "dropoff_zone_id":    row["dropoff_zone_id"],
            "dropoff_zone_name":  row["dropoff_zone_name"],
            "trip_distance_mi":   float(row["trip_distance"]),
            "trip_duration_min":  float(row["trip_duration_min"]),
            "rdi_value":          float(row["rdi_value"]),
            "classification":     row["classification"],
        }
        for row in trip_rows
    ]

    return result
