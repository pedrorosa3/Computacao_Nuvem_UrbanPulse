import grpc
import os
from app import demand_service_pb2, demand_service_pb2_grpc

DEMAND_SERVICE_URL = os.getenv("DEMAND_SERVICE_URL", "demand-api:50053")


def fetch_zone_hourly_demand(zone_id: int) -> dict:
    """
    Chama o Demand Service via gRPC e obtém a contagem de viagens por hora
    para uma zona específica.
    Retorna um dicionário {hora: contagem} ou None em caso de erro.
    """
    try:
        with grpc.insecure_channel(DEMAND_SERVICE_URL) as channel:
            stub = demand_service_pb2_grpc.DemandServiceStub(channel)
            request = demand_service_pb2.ZoneDemandRequest(zone_id=zone_id)
            response = stub.GetZoneHourlyDemand(request, timeout=5)
            return dict(response.hourly_counts)
    except grpc.RpcError as e:
        print(f"Erro gRPC (Demand Service): {e.details()}")
        return None