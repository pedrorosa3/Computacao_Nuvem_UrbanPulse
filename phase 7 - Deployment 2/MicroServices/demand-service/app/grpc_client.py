import grpc
from . import location_service_pb2
from . import location_service_pb2_grpc

# Tens de confirmar com o Diogo qual é a porta gRPC dele! 
# Vamos assumir que é a 50054 por agora.
LOCATION_SERVICE_URL = "host.docker.internal:50054" 

def fetch_zone_info(zone_id: int) -> dict:
    """Vai buscar o nome e bairro da zona ao Location Service."""
    try:
        with grpc.insecure_channel(LOCATION_SERVICE_URL) as channel:
            stub = location_service_pb2_grpc.LocationServiceStub(channel)
            request = location_service_pb2.ZoneNameRequest(zone_id=zone_id)
            
            response = stub.GetZoneName(request, timeout=3)
            return {
                "zone_name": response.zone_name,
                "borough": response.borough
            }
    except grpc.RpcError as e:
        print(f"Erro gRPC (Location Service): {e.details()}")
        return None # Retorna None se o Diogo estiver offline