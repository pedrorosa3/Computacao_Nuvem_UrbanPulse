from fastapi import APIRouter, Query, HTTPException
from datetime import date
from app.database import execute_query

router = APIRouter()

# UC20 — Suspicious trip detection
#
# A trip is flagged as suspicious if it violates one or more of these rules:
#
#   PRICE_VS_DISTANCE  : fare > $3 per mile for short trips (< 2 mi) with fare > $30
#                        i.e. "2km trip costing $50"
#   ZERO_DISTANCE      : fare > $5 but trip_distance = 0
#   NEGATIVE_FARE      : fare_amount < 0
#   IMPOSSIBLE_SPEED   : implied speed > 100 mph  (distance/duration)
#   ZERO_DURATION      : trip_duration_min = 0 but distance > 0
#   TIP_EXCEEDS_FARE   : tip_amount > fare_amount * 2  (tip more than twice the fare)
#   EXCESSIVE_FARE     : fare_amount > 200  (outlier threshold)
#   NEGATIVE_PASSENGERS: passenger_count <= 0


@router.get(
    "/trips/suspicious",
    summary="UC20 — Detect suspicious trips",
    description=(
        "Returns trips that violate business rules and are likely anomalous. "
        "Each flagged trip includes the list of reasons it was flagged."
    ),
)
def get_suspicious_trips(
    start_date:     date = Query(None, description="Filter from this date (inclusive)"),
    end_date:       date = Query(None, description="Filter up to this date (inclusive)"),
    pickup_zone_id:  int = Query(None, description="Filter by pickup zone ID"),
    limit:           int = Query(50, ge=1, le=200, description="Max trips to return"),
    summary_only:   bool = Query(False, description="Return only counts per anomaly type"),
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

    # Summary: count trips per anomaly flag
    summary_query = f"""
        SELECT
            'PRICE_VS_DISTANCE'   AS anomaly,
            COUNT(*)              AS trip_count
        FROM trips {where}
        WHERE trip_distance > 0 AND trip_distance < 2 AND fare_amount > 30
        UNION ALL
        SELECT 'ZERO_DISTANCE',   COUNT(*) FROM trips {where}
        WHERE trip_distance = 0 AND fare_amount > 5
        UNION ALL
        SELECT 'NEGATIVE_FARE',   COUNT(*) FROM trips {where}
        WHERE fare_amount < 0
        UNION ALL
        SELECT 'IMPOSSIBLE_SPEED', COUNT(*) FROM trips {where}
        WHERE trip_duration_min > 0 AND (trip_distance / (trip_duration_min / 60.0)) > 100
        UNION ALL
        SELECT 'ZERO_DURATION',   COUNT(*) FROM trips {where}
        WHERE trip_duration_min = 0 AND trip_distance > 0
        UNION ALL
        SELECT 'TIP_EXCEEDS_FARE', COUNT(*) FROM trips {where}
        WHERE tip_amount > fare_amount * 2 AND fare_amount > 0
        UNION ALL
        SELECT 'EXCESSIVE_FARE',  COUNT(*) FROM trips {where}
        WHERE fare_amount > 200
        UNION ALL
        SELECT 'NEGATIVE_PASSENGERS', COUNT(*) FROM trips {where}
        WHERE passenger_count <= 0
        ORDER BY trip_count DESC
    """
    # Note: the {where} clause repeats — params must be duplicated 8 times
    summary_rows = execute_query(summary_query, tuple(params) * 8)

    total_anomalies = sum(int(r["trip_count"]) for r in summary_rows)

    result = {
        "filters": {
            "start_date":     str(start_date)    if start_date    else None,
            "end_date":       str(end_date)      if end_date      else None,
            "pickup_zone_id": pickup_zone_id,
        },
        "anomaly_rules": {
            "PRICE_VS_DISTANCE":    "trip_distance < 2 miles AND fare > $30",
            "ZERO_DISTANCE":        "trip_distance = 0 AND fare > $5",
            "NEGATIVE_FARE":        "fare_amount < 0",
            "IMPOSSIBLE_SPEED":     "implied speed > 100 mph",
            "ZERO_DURATION":        "duration = 0 min AND distance > 0",
            "TIP_EXCEEDS_FARE":     "tip > 2× fare",
            "EXCESSIVE_FARE":       "fare > $200",
            "NEGATIVE_PASSENGERS":  "passenger_count ≤ 0",
        },
        "total_flagged_trips": total_anomalies,
        "summary": [
            {
                "anomaly":    row["anomaly"],
                "trip_count": int(row["trip_count"]),
            }
            for row in summary_rows
        ],
    }

    if summary_only:
        return result

    # Detailed query: return individual suspicious trips with reason list
    detail_query = f"""
        SELECT
            id,
            tpep_pickup_datetime,
            tpep_dropoff_datetime,
            pickup_zone_id,
            pickup_zone_name,
            dropoff_zone_id,
            dropoff_zone_name,
            trip_distance,
            ROUND(trip_duration_min::numeric, 2)  AS trip_duration_min,
            fare_amount,
            tip_amount,
            total_amount,
            passenger_count,
            ARRAY_REMOVE(ARRAY[
                CASE WHEN trip_distance > 0 AND trip_distance < 2 AND fare_amount > 30
                     THEN 'PRICE_VS_DISTANCE'    END,
                CASE WHEN trip_distance = 0 AND fare_amount > 5
                     THEN 'ZERO_DISTANCE'        END,
                CASE WHEN fare_amount < 0
                     THEN 'NEGATIVE_FARE'        END,
                CASE WHEN trip_duration_min > 0
                          AND (trip_distance / (trip_duration_min / 60.0)) > 100
                     THEN 'IMPOSSIBLE_SPEED'     END,
                CASE WHEN trip_duration_min = 0 AND trip_distance > 0
                     THEN 'ZERO_DURATION'        END,
                CASE WHEN tip_amount > fare_amount * 2 AND fare_amount > 0
                     THEN 'TIP_EXCEEDS_FARE'     END,
                CASE WHEN fare_amount > 200
                     THEN 'EXCESSIVE_FARE'       END,
                CASE WHEN passenger_count <= 0
                     THEN 'NEGATIVE_PASSENGERS'  END
            ], NULL) AS anomaly_flags
        FROM trips
        {where}
        HAVING ARRAY_LENGTH(ARRAY_REMOVE(ARRAY[
            CASE WHEN trip_distance > 0 AND trip_distance < 2 AND fare_amount > 30
                 THEN 'PRICE_VS_DISTANCE'    END,
            CASE WHEN trip_distance = 0 AND fare_amount > 5
                 THEN 'ZERO_DISTANCE'        END,
            CASE WHEN fare_amount < 0
                 THEN 'NEGATIVE_FARE'        END,
            CASE WHEN trip_duration_min > 0
                      AND (trip_distance / (trip_duration_min / 60.0)) > 100
                 THEN 'IMPOSSIBLE_SPEED'     END,
            CASE WHEN trip_duration_min = 0 AND trip_distance > 0
                 THEN 'ZERO_DURATION'        END,
            CASE WHEN tip_amount > fare_amount * 2 AND fare_amount > 0
                 THEN 'TIP_EXCEEDS_FARE'     END,
            CASE WHEN fare_amount > 200
                 THEN 'EXCESSIVE_FARE'       END,
            CASE WHEN passenger_count <= 0
                 THEN 'NEGATIVE_PASSENGERS'  END
        ], NULL), 1) > 0
        ORDER BY ARRAY_LENGTH(anomaly_flags, 1) DESC, fare_amount DESC
        LIMIT %s
    """
    params_detail = tuple(params) + (limit,)
    trip_rows = execute_query(detail_query, params_detail)

    result["trips"] = [
        {
            "trip_id":            row["id"],
            "pickup_datetime":    str(row["tpep_pickup_datetime"]),
            "dropoff_datetime":   str(row["tpep_dropoff_datetime"]),
            "pickup_zone_id":     row["pickup_zone_id"],
            "pickup_zone_name":   row["pickup_zone_name"],
            "dropoff_zone_id":    row["dropoff_zone_id"],
            "dropoff_zone_name":  row["dropoff_zone_name"],
            "trip_distance_mi":   float(row["trip_distance"]) if row["trip_distance"] is not None else None,
            "trip_duration_min":  float(row["trip_duration_min"]) if row["trip_duration_min"] is not None else None,
            "fare_amount":        float(row["fare_amount"])    if row["fare_amount"]    is not None else None,
            "tip_amount":         float(row["tip_amount"])     if row["tip_amount"]     is not None else None,
            "total_amount":       float(row["total_amount"])   if row["total_amount"]   is not None else None,
            "passenger_count":    row["passenger_count"],
            "anomaly_flags":      row["anomaly_flags"],
        }
        for row in trip_rows
    ]

    return result
