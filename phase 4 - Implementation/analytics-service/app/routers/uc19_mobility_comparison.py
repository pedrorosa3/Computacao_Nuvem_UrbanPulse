import grpc
import os
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app import (
    location_service_pb2, location_service_pb2_grpc,
    demand_service_pb2,   demand_service_pb2_grpc,
    payment_service_pb2,  payment_service_pb2_grpc,
)

router = APIRouter()

LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL", "location-api:50054")
DEMAND_SERVICE_URL   = os.getenv("DEMAND_SERVICE_URL",   "demand-service:50053")
PAYMENT_SERVICE_URL  = os.getenv("PAYMENT_SERVICE_URL",  "payment-api:50052")


def _get_zone_groups(start_date: str, end_date: str):
    with grpc.insecure_channel(LOCATION_SERVICE_URL) as channel:
        stub = location_service_pb2_grpc.LocationServiceStub(channel)
        req  = location_service_pb2.ZoneGroupsRequest(
            start_date=start_date or "",
            end_date=end_date or "",
        )
        return stub.GetZoneGroups(req, timeout=10)


def _get_group_demand(zone_ids: list[int]):
    with grpc.insecure_channel(DEMAND_SERVICE_URL) as channel:
        stub = demand_service_pb2_grpc.DemandServiceStub(channel)
        req  = demand_service_pb2.GroupDemandRequest(zone_ids=zone_ids)
        return stub.GetGroupDemand(req, timeout=10)


def _get_payment_distribution(start_date: str, end_date: str):
    with grpc.insecure_channel(PAYMENT_SERVICE_URL) as channel:
        stub = payment_service_pb2_grpc.PaymentServiceStub(channel)
        req  = payment_service_pb2.PaymentDistributionRequest(
            start_date=start_date or "",
            end_date=end_date or "",
        )
        return stub.GetPaymentDistribution(req, timeout=10)


@router.get("/analytics/mobility-comparison")
def mobility_comparison(
    start_date: Optional[str] = Query(None, example="2015-01-01"),
    end_date:   Optional[str] = Query(None, example="2015-12-31"),
):
    # 1. Location Service — trip volumes por grupo
    try:
        zone_groups = _get_zone_groups(start_date, end_date)
    except grpc.RpcError as e:
        raise HTTPException(status_code=503, detail=f"Location Service indisponível: {e.details()}")

    affluent   = zone_groups.affluent
    peripheral = zone_groups.peripheral
    total_trips = zone_groups.total_trips

    # 2. Demand Service — demand patterns por grupo
    # Nota: o Location Service expõe os zone_ids por grupo via GetZoneGroups
    # Para simplificar, chamamos GetGroupDemand com os IDs de cada grupo
    # Os IDs são obtidos internamente no Location Service — aqui usamos
    # uma chamada separada apenas para o demo. Em produção, o proto
    # poderia incluir os zone_ids na resposta.
    affluent_demand, peripheral_demand = None, None
    try:
        # Chamar demand para affluent e peripheral
        # Como não temos os zone_ids aqui, passamos listas vazias por agora
        # TODO: Location Service devolver zone_ids em ZoneGroupsResponse
        affluent_ids_list   = list(zone_groups.affluent.zone_ids)
        peripheral_ids_list = list(zone_groups.peripheral.zone_ids)
        affluent_demand_resp   = _get_group_demand(affluent_ids_list)
        peripheral_demand_resp = _get_group_demand(peripheral_ids_list)
        affluent_demand = {
            "peak_hour": affluent_demand_resp.peak_hour,
            "avg_volatility_index": round(affluent_demand_resp.avg_volatility_index, 2),
            "volatility_classification": affluent_demand_resp.volatility_classification,
        }
        peripheral_demand = {
            "peak_hour": peripheral_demand_resp.peak_hour,
            "avg_volatility_index": round(peripheral_demand_resp.avg_volatility_index, 2),
            "volatility_classification": peripheral_demand_resp.volatility_classification,
        }
    except grpc.RpcError as e:
        print(f"Demand Service indisponível: {e.details()}")

    # 3. Payment Service — distribuição de pagamentos
    payment_dist = {"card_payment_pct": None, "cash_payment_pct": None}
    try:
        pay = _get_payment_distribution(start_date, end_date)
        payment_dist = {
            "card_payment_pct": round(pay.card_payment_pct, 2),
            "cash_payment_pct": round(pay.cash_payment_pct, 2),
        }
    except grpc.RpcError as e:
        print(f"Payment Service indisponível: {e.details()}")

    # 4. Revenue Service — TODO
    empty_financials = {
        "avg_fare":    None,  # TODO: Revenue Service
        "avg_tip":     None,  # TODO: Revenue Service
        "avg_tip_pct": None,  # TODO: Revenue Service
    }

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
                "financials": empty_financials,
                "payments":   payment_dist,
                "demand":     affluent_demand,
            },
            "peripheral": {
                "zone_count":  peripheral.zone_count,
                "trip_volume": {
                    "total_trips":      peripheral.total_trips,
                    "market_share_pct": round(peripheral.market_share_pct, 2),
                },
                "financials": empty_financials,
                "payments":   payment_dist,
                "demand":     peripheral_demand,
            },
        },
        "mobility_gap": {
            "trip_volume_gap_pct":  gap(affluent.market_share_pct, peripheral.market_share_pct),
            "fare_gap_pct":         None,  # TODO: Revenue Service
            "tip_gap_pct":          None,  # TODO: Revenue Service
            "card_payment_gap_pct": None,  # TODO: Payment por zona
        },
    }
