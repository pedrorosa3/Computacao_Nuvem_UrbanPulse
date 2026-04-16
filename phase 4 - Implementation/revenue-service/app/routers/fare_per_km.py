from fastapi import APIRouter, HTTPException, Query
from typing import Literal, Optional
import grpc
import os

from app import trip_service_pb2, trip_service_pb2_grpc
from app import location_service_pb2, location_service_pb2_grpc
from app.db.connection import get_conn

router = APIRouter()

TRIP_SERVICE_HOST     = os.getenv("TRIP_SERVICE_HOST",     "trip-api")
TRIP_SERVICE_PORT     = os.getenv("TRIP_SERVICE_PORT",     "50051")
LOCATION_SERVICE_HOST = os.getenv("LOCATION_SERVICE_HOST", "location-api")
LOCATION_SERVICE_PORT = os.getenv("LOCATION_SERVICE_PORT", "50054")


def _get_trip_stub():
    channel = grpc.insecure_channel(f"{TRIP_SERVICE_HOST}:{TRIP_SERVICE_PORT}")
    return trip_service_pb2_grpc.TripServiceStub(channel)


def _get_location_stub():
    channel = grpc.insecure_channel(f"{LOCATION_SERVICE_HOST}:{LOCATION_SERVICE_PORT}")
    return location_service_pb2_grpc.LocationServiceStub(channel)


@router.get("/fare-per-km", summary="UC10 – Preço médio por km por zona")
def fare_per_km(
    zone_type: Literal["pickup", "dropoff"] = Query(default="pickup"),
    year:      Optional[int]                = Query(default=None),
    month:     Optional[int]                = Query(default=None, ge=1, le=12),
    order_by:  Literal["fare_per_km", "zone_id"] = Query(default="fare_per_km"),
    limit:     int                          = Query(default=20, ge=1, le=200),
):
    zone_col = f"{zone_type}_zone_id"

    conditions = ["fare_amount > 0"]
    params: list = []

    if year:
        conditions.append("EXTRACT(YEAR FROM pickup_date) = %s")
        params.append(year)
    if month:
        conditions.append("EXTRACT(MONTH FROM pickup_date) = %s")
        params.append(month)

    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            {zone_col}       AS zone_id,
            AVG(fare_amount) AS avg_fare,
            COUNT(*)         AS trip_count
        FROM trips
        {where}
        GROUP BY {zone_col}
    """

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not rows:
        return {"results": [], "filters": {"zone_type": zone_type, "year": year, "month": month}, "total": 0}

    fare_map = {row["zone_id"]: {"avg_fare": float(row["avg_fare"]), "trip_count": row["trip_count"]} for row in rows}

    # ── gRPC ao Trip Service
    try:
        stub = _get_trip_stub()
        grpc_response = stub.GetDistanceByZone(
            trip_service_pb2.DistanceByZoneRequest(
                zone_type=zone_type,
                year=year  if year  else 0,
                month=month if month else 0,
            ),
            timeout=10,
        )
    except grpc.RpcError as e:
        raise HTTPException(status_code=502, detail=f"Trip Service gRPC error: {e.code()} — {e.details()}")

    distance_map = {z.zone_id: z.avg_distance for z in grpc_response.zones}

    # ── gRPC ao Location Service 
    zone_ids = list(fare_map.keys())
    zone_info: dict[int, dict] = {}
    try:
        loc_stub = _get_location_stub()
        loc_response = loc_stub.GetZoneNames(
            location_service_pb2.ZoneNamesRequest(zone_ids=zone_ids),
            timeout=5,
        )
        zone_info = {z.zone_id: {"zone_name": z.zone_name, "borough": z.borough} for z in loc_response.zones}
    except grpc.RpcError:
        pass  

    
    results = []
    for zone_id, fd in fare_map.items():
        avg_dist = distance_map.get(zone_id)
        if not avg_dist or avg_dist <= 0:
            continue
        info = zone_info.get(zone_id, {})
        results.append({
            "zone_id":         zone_id,
            "zone_name":       info.get("zone_name"),
            "borough":         info.get("borough"),
            "fare_per_km":     round(fd["avg_fare"] / avg_dist, 4),
            "avg_fare":        round(fd["avg_fare"], 4),
            "avg_distance_km": round(avg_dist, 4),
            "trip_count":      fd["trip_count"],
        })

    results.sort(key=lambda r: r[order_by], reverse=(order_by == "fare_per_km"))
    results = results[:limit]

    return {
        "results": results,
        "filters": {"zone_type": zone_type, "year": year, "month": month, "order_by": order_by, "limit": limit},
        "total": len(results),
    }
