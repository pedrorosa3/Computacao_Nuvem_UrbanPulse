import grpc
import os
import math
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app import (
    trip_service_pb2,
    trip_service_pb2_grpc,
    revenue_service_pb2,
    revenue_service_pb2_grpc,
)

router = APIRouter()

TRIP_SERVICE_URL    = os.getenv("TRIP_SERVICE_URL",    "trip-api:50051")
REVENUE_SERVICE_URL = os.getenv("REVENUE_SERVICE_URL", "revenue-api:50055")


def safe_float(value, default=0.0):
    """Converte para float seguro para JSON (sem inf/nan)."""
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, 4)
    except (TypeError, ValueError):
        return default


def _get_suspicious_trips(min_score: int, start_date: str, end_date: str, limit: int):
    with grpc.insecure_channel(TRIP_SERVICE_URL) as channel:
        stub = trip_service_pb2_grpc.TripServiceStub(channel)
        req  = trip_service_pb2.SuspiciousTripsRequest(
            min_suspicion_score = min_score,
            start_date          = start_date or "",
            end_date            = end_date   or "",
            limit               = limit,
        )
        return stub.GetSuspiciousTrips(req, timeout=10)


def _get_trip_revenues(trip_ids: list[int]):
    with grpc.insecure_channel(REVENUE_SERVICE_URL) as channel:
        stub = revenue_service_pb2_grpc.RevenueServiceStub(channel)
        req  = revenue_service_pb2.TripRevenueRequest(trip_ids=trip_ids)
        return stub.GetTripRevenues(req, timeout=10)


@router.get(
    "/analytics/anomalous-trips",
    summary="UC20 — Viagens anómalas",
    description=(
        "Agrega dados do Trip Service (viagens suspeitas) e Revenue Service (tarifas) via gRPC. "
        "Identifica e classifica viagens com comportamento anómalo cruzando o suspicion_score "
        "com dados de receita do Revenue Service."
    ),
)
def anomalous_trips(
    min_suspicion_score: int           = Query(1, ge=1, le=7, description="Score mínimo (1-7)"),
    start_date:          Optional[str] = Query(None, example="2015-01-01"),
    end_date:            Optional[str] = Query(None, example="2015-01-31"),
    limit:               int           = Query(50, ge=1, le=200),
):
    # 1. Trip Service → viagens suspeitas
    try:
        suspicious_resp = _get_suspicious_trips(
            min_suspicion_score, start_date or "", end_date or "", limit
        )
    except grpc.RpcError as e:
        raise HTTPException(status_code=503, detail=f"Trip Service indisponível: {e.details()}")

    trips       = list(suspicious_resp.trips)
    total_found = suspicious_resp.total_found

    if not trips:
        return {
            "total_found":         0,
            "returned":            0,
            "min_suspicion_score": min_suspicion_score,
            "trips":               [],
        }

    trip_ids = [t.trip_id for t in trips]

    # 2. Revenue Service → tarifas para cruzar
    try:
        revenue_resp = _get_trip_revenues(trip_ids)
        revenue_map  = {r.trip_id: r for r in revenue_resp.revenues}
        revenue_used = True
    except grpc.RpcError as e:
        print(f"Revenue Service indisponível: {e.details()}")
        revenue_map  = {}
        revenue_used = False

    # 3. Classificar por score
    def anomaly_label(score: int) -> str:
        if score >= 4: return "critical"
        if score >= 2: return "high"
        return "low"

    score_distribution = {"low": 0, "high": 0, "critical": 0}
    result_trips = []

    for t in trips:
        label = anomaly_label(t.suspicion_score)
        score_distribution[label] += 1

        trip_data = {
            "trip_id":          t.trip_id,
            "pickup_zone":      t.pickup_zone,
            "dropoff_zone":     t.dropoff_zone,
            "trip_distance_km": safe_float(t.trip_distance_km),
            "fare_amount":      safe_float(t.fare_amount),
            "deviation_index":  safe_float(t.deviation_index),
            "deviation_class":  t.deviation_class,
            "suspicion_score":  t.suspicion_score,
            "anomaly_label":    label,
        }

        # Enriquecer com Revenue Service
        if revenue_used and t.trip_id in revenue_map:
            rev = revenue_map[t.trip_id]
            fare_trip    = safe_float(t.fare_amount)
            fare_revenue = safe_float(rev.fare_amount)
            discrepancy  = round(abs(fare_trip - fare_revenue), 2)
            trip_data["revenue"] = {
                "fare_amount":      safe_float(rev.fare_amount),
                "total_amount":     safe_float(rev.total_amount),
                "tip_amount":       safe_float(rev.tip_amount),
                "fare_discrepancy": discrepancy,
                "suspicious_fare":  discrepancy > 5.0,
            }

        result_trips.append(trip_data)

    return {
        "sources": {
            "trip_service":    TRIP_SERVICE_URL,
            "revenue_service": REVENUE_SERVICE_URL,
        },
        "filters": {
            "min_suspicion_score": min_suspicion_score,
            "start_date":          start_date,
            "end_date":            end_date,
        },
        "total_found":          total_found,
        "returned":             len(result_trips),
        "revenue_service_used": revenue_used,
        "score_distribution":   score_distribution,
        "anomaly_labels": {
            "low":      "suspicion_score = 1",
            "high":     "suspicion_score = 2-3",
            "critical": "suspicion_score >= 4",
        },
        "trips": result_trips,
    }
