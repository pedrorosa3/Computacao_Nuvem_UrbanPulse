import grpc
import os
import time
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app import (
    location_service_pb2, location_service_pb2_grpc,
    demand_service_pb2,   demand_service_pb2_grpc,
    payment_service_pb2,  payment_service_pb2_grpc,
    revenue_service_pb2,  revenue_service_pb2_grpc,
)
from app.metrics import GRPC_REQUESTS_TOTAL, GRPC_REQUEST_DURATION

router = APIRouter()

LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL", "location-api:50054")
DEMAND_SERVICE_URL   = os.getenv("DEMAND_SERVICE_URL",   "demand-service:50053")
PAYMENT_SERVICE_URL  = os.getenv("PAYMENT_SERVICE_URL",  "payment-svc:50052")
REVENUE_SERVICE_URL  = os.getenv("REVENUE_SERVICE_URL",  "revenue-service:50055")


def _grpc_call(target_service: str, method: str, fn):
    """Executa uma chamada gRPC e regista métricas de latência e status."""
    start = time.perf_counter()
    status = "ok"
    try:
        return fn()
    except grpc.RpcError as e:
        status = e.code().name  # ex: UNAVAILABLE, DEADLINE_EXCEEDED
        raise
    finally:
        elapsed = time.perf_counter() - start
        GRPC_REQUESTS_TOTAL.labels(target_service, method, status).inc()
        GRPC_REQUEST_DURATION.labels(target_service, method).observe(elapsed)


def _get_zone_groups(start_date: str, end_date: str):
    def call():
        with grpc.insecure_channel(LOCATION_SERVICE_URL) as channel:
            stub = location_service_pb2_grpc.LocationServiceStub(channel)
            req  = location_service_pb2.ZoneGroupsRequest(
                start_date=start_date or "",
                end_date=end_date or "",
            )
            return stub.GetZoneGroups(req, timeout=10)
    return _grpc_call("location", "GetZoneGroups", call)


def _get_group_demand(zone_ids: list[int]):
    def call():
        with grpc.insecure_channel(DEMAND_SERVICE_URL) as channel:
            stub = demand_service_pb2_grpc.DemandServiceStub(channel)
            req  = demand_service_pb2.GroupDemandRequest(zone_ids=zone_ids)
            return stub.GetGroupDemand(req, timeout=10)
    return _grpc_call("demand", "GetGroupDemand", call)


def _get_payment_distribution(start_date: str, end_date: str):
    def call():
        with grpc.insecure_channel(PAYMENT_SERVICE_URL) as channel:
            stub = payment_service_pb2_grpc.PaymentServiceStub(channel)
            req  = payment_service_pb2.PaymentDistributionRequest(
                start_date=start_date or "",
                end_date=end_date or "",
            )
            return stub.GetPaymentDistribution(req, timeout=10)
    return _grpc_call("payment", "GetPaymentDistribution", call)


def _get_zone_group_payment(zone_ids: list[int]):
    def call():
        with grpc.insecure_channel(PAYMENT_SERVICE_URL) as channel:
            stub = payment_service_pb2_grpc.PaymentServiceStub(channel)
            req  = payment_service_pb2.ZoneGroupPaymentRequest(zone_ids=zone_ids)
            return stub.GetZoneGroupPayment(req, timeout=10)
    return _grpc_call("payment", "GetZoneGroupPayment", call)


def _get_zone_group_revenue(zone_ids: list[int]):
    def call():
        with grpc.insecure_channel(REVENUE_SERVICE_URL) as channel:
            stub = revenue_service_pb2_grpc.RevenueServiceStub(channel)
            req  = revenue_service_pb2.ZoneGroupRevenueRequest(zone_ids=zone_ids)
            return stub.GetZoneGroupRevenue(req, timeout=10)
    return _grpc_call("revenue", "GetZoneGroupRevenue", call)


@router.get("/analytics/mobility-comparison")
def mobility_comparison(
    start_date: Optional[str] = Query(None, example="2015-01-01"),
    end_date:   Optional[str] = Query(None, example="2015-12-31"),
):
    # 1. Location Service — trip volumes + zone_ids por grupo
    try:
        zone_groups = _get_zone_groups(start_date, end_date)
    except grpc.RpcError as e:
        raise HTTPException(status_code=503, detail=f"Location Service indisponível: {e.details()}")

    affluent       = zone_groups.affluent
    peripheral     = zone_groups.peripheral
    total_trips    = zone_groups.total_trips
    affluent_ids   = list(affluent.zone_ids)
    peripheral_ids = list(peripheral.zone_ids)

    # 2. Demand Service — demand patterns por grupo
    affluent_demand, peripheral_demand = None, None
    try:
        affluent_demand_resp   = _get_group_demand(affluent_ids)
        peripheral_demand_resp = _get_group_demand(peripheral_ids)
        affluent_demand = {
            "peak_hour":                 affluent_demand_resp.peak_hour,
            "avg_volatility_index":      round(affluent_demand_resp.avg_volatility_index, 2),
            "volatility_classification": affluent_demand_resp.volatility_classification,
        }
        peripheral_demand = {
            "peak_hour":                 peripheral_demand_resp.peak_hour,
            "avg_volatility_index":      round(peripheral_demand_resp.avg_volatility_index, 2),
            "volatility_classification": peripheral_demand_resp.volatility_classification,
        }
    except grpc.RpcError as e:
        print(f"Demand Service indisponível: {e.details()}")

    # 3. Payment Service — distribuição por grupo de zonas
    affluent_payments   = {"card_payment_pct": None, "cash_payment_pct": None}
    peripheral_payments = {"card_payment_pct": None, "cash_payment_pct": None}
    try:
        aff_pay = _get_zone_group_payment(affluent_ids)
        affluent_payments = {
            "card_payment_pct": round(aff_pay.card_payment_pct, 2),
            "cash_payment_pct": round(aff_pay.cash_payment_pct, 2),
        }
        per_pay = _get_zone_group_payment(peripheral_ids)
        peripheral_payments = {
            "card_payment_pct": round(per_pay.card_payment_pct, 2),
            "cash_payment_pct": round(per_pay.cash_payment_pct, 2),
        }
    except grpc.RpcError as e:
        print(f"Payment Service indisponível: {e.details()}")

    # 4. Revenue Service — financials por grupo
    affluent_financials   = {"avg_fare": None, "avg_tip": None, "avg_tip_pct": None}
    peripheral_financials = {"avg_fare": None, "avg_tip": None, "avg_tip_pct": None}
    try:
        aff_rev = _get_zone_group_revenue(affluent_ids)
        affluent_financials = {
            "avg_fare":    aff_rev.avg_fare,
            "avg_tip":     aff_rev.avg_tip,
            "avg_tip_pct": aff_rev.avg_tip_pct,
        }
        per_rev = _get_zone_group_revenue(peripheral_ids)
        peripheral_financials = {
            "avg_fare":    per_rev.avg_fare,
            "avg_tip":     per_rev.avg_tip,
            "avg_tip_pct": per_rev.avg_tip_pct,
        }
    except grpc.RpcError as e:
        print(f"Revenue Service indisponível: {e.details()}")

    # 5. Mobility gap
    def gap(a, b):
        if a is None or b is None or b == 0:
            return None
        return round((a - b) / b * 100, 2)

    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "total_trips": total_trips,
        "zone_classifications": {
            "affluent":   "Manhattan Yellow Zone",
            "peripheral": "Bronx, Staten Island and Boro Zones",
        },
        "comparison": {
            "affluent": {
                "zone_count":  affluent.zone_count,
                "trip_volume": {
                    "total_trips":      affluent.total_trips,
                    "market_share_pct": round(affluent.market_share_pct, 2),
                },
                "financials": affluent_financials,
                "payments":   affluent_payments,
                "demand":     affluent_demand,
            },
            "peripheral": {
                "zone_count":  peripheral.zone_count,
                "trip_volume": {
                    "total_trips":      peripheral.total_trips,
                    "market_share_pct": round(peripheral.market_share_pct, 2),
                },
                "financials": peripheral_financials,
                "payments":   peripheral_payments,
                "demand":     peripheral_demand,
            },
        },
        "mobility_gap (Zonas Peripheral VS Affluent - Tudo em %)": {
            "trip_volume_gap_pct":  gap(affluent.market_share_pct,             peripheral.market_share_pct),
            "fare_gap_pct":         gap(affluent_financials["avg_fare"],        peripheral_financials["avg_fare"]),
            "tip_gap_pct":          gap(affluent_financials["avg_tip"],         peripheral_financials["avg_tip"]),
            "card_payment_gap_pct": gap(affluent_payments["card_payment_pct"],  peripheral_payments["card_payment_pct"]),
        },
    }