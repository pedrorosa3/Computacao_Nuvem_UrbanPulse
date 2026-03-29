import grpc
import os
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app import (
    trip_service_pb2,
    trip_service_pb2_grpc,
    payment_service_pb2,
    payment_service_pb2_grpc,
)

router = APIRouter()

TRIP_SERVICE_URL    = os.getenv("TRIP_SERVICE_URL",    "trip-api:50051")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "payment-api:50052")

# Busca um sample de trip_ids para analisar (sem filtro por data no Trip Service gRPC,
# usamos os IDs directamente — em produção o proto poderia ter filtro de data)
SAMPLE_SIZE = 500


def _get_trip_durations(trip_ids: list[int]):
    with grpc.insecure_channel(TRIP_SERVICE_URL) as channel:
        stub = trip_service_pb2_grpc.TripServiceStub(channel)
        req  = trip_service_pb2.TripDurationRequest(trip_ids=trip_ids)
        return stub.GetTripDurations(req, timeout=10)


def _get_payment_details(trip_ids: list[int]):
    with grpc.insecure_channel(PAYMENT_SERVICE_URL) as channel:
        stub = payment_service_pb2_grpc.PaymentServiceStub(channel)
        req  = payment_service_pb2.PaymentRequest(trip_ids=trip_ids)
        return stub.GetPaymentDetails(req, timeout=10)


@router.get(
    "/analytics/duration-tip-correlation",
    summary="UC18 — Correlação duração vs gorjeta",
    description=(
        "Agrega dados do Trip Service (duração) e Payment Service (gorjetas) via gRPC. "
        "Calcula a correlação entre duração da viagem e valor da gorjeta, "
        "por período do dia (peak / off_peak / night). "
        "Apenas viagens com pagamento por cartão são incluídas (cash tips não são registados)."
    ),
)
def duration_tip_correlation(
    limit: int = Query(500, ge=10, le=2000, description="Número de viagens a analisar"),
):
    # 1. Buscar IDs de viagens ao Trip Service
    # Usamos IDs sequenciais como amostra
    trip_ids = list(range(1, limit + 1))

    # 2. Trip Service → durações
    try:
        duration_resp = _get_trip_durations(trip_ids)
    except grpc.RpcError as e:
        raise HTTPException(status_code=503, detail=f"Trip Service indisponível: {e.details()}")

    # 3. Payment Service → gorjetas
    try:
        payment_resp = _get_payment_details(trip_ids)
    except grpc.RpcError as e:
        raise HTTPException(status_code=503, detail=f"Payment Service indisponível: {e.details()}")

    # 4. Cruzar dados — só viagens com cartão (tip registado)
    payments_map = dict(payment_resp.payments)  # {trip_id: TripPaymentInfo}

    matched = []
    for trip in duration_resp.trips:
        pay = payments_map.get(trip.trip_id)
        if pay and pay.payment_type == "card" and trip.duration_min > 0:
            matched.append({
                "trip_id":      trip.trip_id,
                "duration_min": trip.duration_min,
                "distance_km":  trip.distance_km,
                "time_class":   trip.time_class,
                "tip_amount":   pay.tip_amount,
                "fare_amount":  pay.fare_amount,
            })

    if not matched:
        return {
            "total_trips_analysed": 0,
            "note": "Sem dados suficientes para análise.",
            "by_period": [],
        }

    # 5. Calcular estatísticas por período
    from collections import defaultdict
    by_period = defaultdict(list)
    for t in matched:
        by_period[t["time_class"]].append(t)

    def pearson(xs, ys):
        n = len(xs)
        if n < 2:
            return None
        mx = sum(xs) / n
        my = sum(ys) / n
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
        return round(num / den, 4) if den != 0 else None

    def strength(r):
        if r is None:
            return "insufficient data"
        r = abs(r)
        if r < 0.1:   return "negligible"
        if r < 0.3:   return "weak"
        if r < 0.5:   return "moderate"
        if r < 0.7:   return "strong"
        return "very strong"

    period_results = []
    all_durations = [t["duration_min"] for t in matched]
    all_tips      = [t["tip_amount"]   for t in matched]

    for period in ["peak", "off_peak", "night"]:
        trips_p = by_period.get(period, [])
        if not trips_p:
            continue
        durations = [t["duration_min"] for t in trips_p]
        tips      = [t["tip_amount"]   for t in trips_p]
        r         = pearson(durations, tips)

        # Bucket analysis
        buckets = {"0-10 min": [], "10-20 min": [], "20-30 min": [], "30-60 min": [], "60+ min": []}
        for t in trips_p:
            d = t["duration_min"]
            if d < 10:   buckets["0-10 min"].append(t["tip_amount"])
            elif d < 20: buckets["10-20 min"].append(t["tip_amount"])
            elif d < 30: buckets["20-30 min"].append(t["tip_amount"])
            elif d < 60: buckets["30-60 min"].append(t["tip_amount"])
            else:        buckets["60+ min"].append(t["tip_amount"])

        bucket_stats = []
        for bucket, tips_b in buckets.items():
            if tips_b:
                bucket_stats.append({
                    "duration_bucket": bucket,
                    "trip_count":      len(tips_b),
                    "avg_tip":         round(sum(tips_b) / len(tips_b), 2),
                    "max_tip":         round(max(tips_b), 2),
                })

        period_results.append({
            "period":                period,
            "trip_count":            len(trips_p),
            "avg_duration_min":      round(sum(durations) / len(durations), 2),
            "avg_tip":               round(sum(tips) / len(tips), 2),
            "pearson_correlation":   r,
            "correlation_strength":  strength(r),
            "duration_buckets":      bucket_stats,
        })

    global_r = pearson(all_durations, all_tips)

    return {
        "sources": {
            "trip_service":    TRIP_SERVICE_URL,
            "payment_service": PAYMENT_SERVICE_URL,
        },
        "note": "Apenas viagens com pagamento por cartão (cash tips não são registados).",
        "total_trips_analysed": len(matched),
        "global_pearson_correlation": global_r,
        "global_correlation_strength": strength(global_r),
        "by_period": period_results,
    }
