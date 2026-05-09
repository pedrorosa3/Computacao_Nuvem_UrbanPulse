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


@router.get("/avg-fare-by-zone", summary="UC08 – Average fare per zone with deviation from global average")
def avg_fare_by_zone(
    zone_type:  str           = Query("pickup", enum=["pickup", "dropoff"]),
    zone_id:    Optional[int] = Query(None, example=161),
    start_date: Optional[str] = Query(None, example="2015-01-01"),
    end_date:   Optional[str] = Query(None, example="2015-12-31"),
    sort:       str           = Query("desc", enum=["asc", "desc"]),
    limit:      int           = Query(20, ge=1, le=263),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    use_cache = (
    zone_id is None and
    start_date is None and
    end_date is None
    )

    cache_key = (
        f"revenue:avg-fare-by-zone:"
        f"zone_type:{zone_type}:"
        f"sort:{sort}:"
        f"limit:{limit}:"
        f"v1"
    )
    
    if use_cache:
        cached_response = _cache_get(cache_key)

        if cached_response is not None:
            return cached_response

    zone_col = "pickup_zone_id" if zone_type == "pickup" else "dropoff_zone_id"

    conditions = ["fare_amount > 0"]
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
        WITH zone_stats AS (
            SELECT
                {zone_col}              AS zone_id,
                AVG(fare_amount)        AS avg_fare,
                COUNT(*)                AS trip_count
            FROM trips
            {where}
            GROUP BY {zone_col}
        ),
        global_avg AS (
            SELECT AVG(fare_amount) AS global_avg_fare
            FROM trips
            {where}
        )
        SELECT
            zs.zone_id,
            ROUND(zs.avg_fare::NUMERIC, 2)                                                     AS avg_fare,
            ROUND((zs.avg_fare - ga.global_avg_fare)::NUMERIC, 2)                              AS deviation_absolute,
            ROUND(((zs.avg_fare - ga.global_avg_fare) / ga.global_avg_fare * 100)::NUMERIC, 2) AS deviation_percentage,
            zs.trip_count,
            ROUND(ga.global_avg_fare::NUMERIC, 2)                                              AS global_avg_fare
        FROM zone_stats zs, global_avg ga
        ORDER BY avg_fare {sort.upper()}
        LIMIT %s
    """
    params_query = params + params + [limit]

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params_query)
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not rows:
        response = {
            "filters_applied": {
                "zone_type": zone_type, "zone_id": zone_id,
                "start_date": start_date, "end_date": end_date,
                "sort": sort, "limit": limit,
            },
            "global_avg_fare": None,
            "zones": [],
        }
        if use_cache:
            _cache_set(cache_key, response)
        return response

    zone_ids = [r["zone_id"] for r in rows]
    zone_info: dict[int, dict] = {}

    try:
        stub = _get_location_stub()
        grpc_response = stub.GetZoneNames(
            location_service_pb2.ZoneNamesRequest(zone_ids=zone_ids),
            timeout=5,
        )
        zone_info = {z.zone_id: {"zone_name": z.zone_name, "borough": z.borough} for z in grpc_response.zones}
    except grpc.RpcError:
        pass

    global_avg_fare = float(rows[0]["global_avg_fare"])

    response = {
        "filters_applied": {
            "zone_type":  zone_type,
            "zone_id":    zone_id,
            "start_date": start_date,
            "end_date":   end_date,
            "sort":       sort,
            "limit":      limit,
        },
        "global_avg_fare": global_avg_fare,
        "zones": [
            {
                "zone_id":              r["zone_id"],
                "zone_name":            zone_info.get(r["zone_id"], {}).get("zone_name"),
                "borough":              zone_info.get(r["zone_id"], {}).get("borough"),
                "avg_fare":             float(r["avg_fare"]),
                "deviation_absolute":   float(r["deviation_absolute"]),
                "deviation_percentage": float(r["deviation_percentage"]),
                "trip_count":           r["trip_count"],
            }
            for r in rows
        ],
    }
    if use_cache:
        _cache_set(cache_key, response)
    return response
