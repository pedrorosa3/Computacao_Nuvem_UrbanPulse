from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import grpc
import os
import json
import redis

from app.db.connection import get_conn
from app import location_service_pb2, location_service_pb2_grpc

router = APIRouter()

LOCATION_SERVICE_HOST = os.getenv("LOCATION_SERVICE_HOST", "location-api")
LOCATION_SERVICE_PORT = os.getenv("LOCATION_SERVICE_PORT", "50054")
REDIS_URL = os.getenv("REDIS_URL")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))

redis_client = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None


def _cache_get(cache_key: str):
    if not redis_client:
        return None
    try:
        cached = redis_client.get(cache_key)
        return json.loads(cached) if cached else None
    except Exception:
        return None


def _cache_set(cache_key: str, value: dict) -> None:
    if not redis_client:
        return
    try:
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(value))
    except Exception:
        pass


def _get_location_stub():
    channel = grpc.insecure_channel(f"{LOCATION_SERVICE_HOST}:{LOCATION_SERVICE_PORT}")
    return location_service_pb2_grpc.LocationServiceStub(channel)


@router.get("/breakdown", summary="UC09 – Percentage breakdown of trip revenue")
def revenue_breakdown(
    zone_id:    Optional[int] = Query(None, example=161),
    zone_type:  str           = Query("pickup", enum=["pickup", "dropoff"]),
    start_date: Optional[str] = Query(None, example="2015-01-01"),
    end_date:   Optional[str] = Query(None, example="2015-12-31"),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    use_cache = (
    zone_id is None and
    start_date is None and
    end_date is None
    )

    cache_key = f"revenue:breakdown:zone_type:{zone_type}:v1"   

    if use_cache:
        cached_response = _cache_get(cache_key)

        if cached_response is not None:
            return cached_response

    zone_col = "pickup_zone_id" if zone_type == "pickup" else "dropoff_zone_id"

    conditions = ["total_amount > 0", "fare_amount > 0"]
    params: list = []
    if zone_id is not None:
        conditions.append(f"{zone_col} = %s")
        params.append(zone_id)
    if start_date:
        conditions.append("pickup_date >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("pickup_date <= %s")
        params.append(end_date)

    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            COUNT(*)                                        AS trip_count,
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
        return {
            "filters_applied": {
                "zone_id":    zone_id,
                "zone_name":  None,
                "borough":    None,
                "zone_type":  zone_type,
                "start_date": start_date,
                "end_date":   end_date,
            },
            "trip_count": 0,
            "avg_total_amount": 0.0,
            "breakdown": {},
            "message": "No trips found for the given filters.",
        }

    # ── gRPC ao Location Service (só se foi passado zone_id)
    zone_name = None
    borough = None
    if zone_id is not None:
        try:
            stub = _get_location_stub()
            loc_response = stub.GetZoneName(
                location_service_pb2.ZoneNameRequest(zone_id=zone_id),
                timeout=5,
            )
            zone_name = loc_response.zone_name or None
            borough = loc_response.borough or None
        except grpc.RpcError:
            pass

    avg_total = float(row["avg_total"])
    avg_fare = float(row["avg_fare"])
    avg_tip = float(row["avg_tip"])
    avg_tolls = float(row["avg_tolls"])
    avg_mta = float(row["avg_mta"])
    avg_sur = float(row["avg_surcharge"])
    avg_extra = float(row["avg_extra"])

    def pct(val: float) -> float:
        return round(val / avg_total * 100, 2) if avg_total else 0.0

    response = {
        "filters_applied": {
            "zone_id":    zone_id,
            "zone_name":  zone_name,
            "borough":    borough,
            "zone_type":  zone_type,
            "start_date": start_date,
            "end_date":   end_date,
        },
        "trip_count":       int(row["trip_count"]),
        "avg_total_amount": round(avg_total, 2),
        "breakdown": {
            "fare_amount":           {"avg": round(avg_fare, 2), "percentage": pct(avg_fare)},
            "tip_amount":            {"avg": round(avg_tip, 2), "percentage": pct(avg_tip)},
            "tolls_amount":          {"avg": round(avg_tolls, 2), "percentage": pct(avg_tolls)},
            "mta_tax":               {"avg": round(avg_mta, 2), "percentage": pct(avg_mta)},
            "improvement_surcharge": {"avg": round(avg_sur, 2), "percentage": pct(avg_sur)},
            "extra":                 {"avg": round(avg_extra, 2), "percentage": pct(avg_extra)},
        },
    }
    if use_cache:
        _cache_set(cache_key, response)
    return response
