import grpc
import os
import time
from app import demand_service_pb2, demand_service_pb2_grpc
from app.metrics import GRPC_REQUESTS_TOTAL, GRPC_REQUEST_DURATION

DEMAND_SERVICE_URL = os.getenv("DEMAND_SERVICE_URL", "demand-service:50053")


def fetch_zone_hourly_demand(zone_id: int) -> dict | None:
    """
    Chama o Demand Service via gRPC e obtém a contagem de viagens por hora
    e o dia de pico para uma zona específica.
    Retorna {"hourly_counts": {hora: contagem}, "peak_day": "Monday"} ou None em caso de erro.
    """
    start = time.perf_counter()
    status = "ok"
    try:
        with grpc.insecure_channel(DEMAND_SERVICE_URL) as channel:
            stub = demand_service_pb2_grpc.DemandServiceStub(channel)
            request = demand_service_pb2.ZoneDemandRequest(zone_id=zone_id)
            response = stub.GetZoneHourlyDemand(request, timeout=5)
            return {
                "hourly_counts": dict(response.hourly_counts),
                "peak_day":      response.peak_day or None,
            }
    except grpc.RpcError as e:
        status = e.code().name
        print(f"Erro gRPC (Demand Service): {e.details()}")
        return None
    finally:
        elapsed = time.perf_counter() - start
        GRPC_REQUESTS_TOTAL.labels("demand", "GetZoneHourlyDemand", status).inc()
        GRPC_REQUEST_DURATION.labels("demand", "GetZoneHourlyDemand").observe(elapsed)