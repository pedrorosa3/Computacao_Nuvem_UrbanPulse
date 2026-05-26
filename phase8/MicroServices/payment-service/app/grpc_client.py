import os

import grpc
from . import trip_service_pb2
from . import trip_service_pb2_grpc


TRIP_SERVICE_URL = os.getenv("TRIP_SERVICE_URL", "trip-api:50051")

def fetch_passenger_counts(trip_ids: list[int]) -> dict:
    """Faz um pedido gRPC ao Trip Service para obter os passageiros de uma lista de viagens."""
    try:
        # Abre um canal de comunicação com o serviço do Guilherme
        with grpc.insecure_channel(TRIP_SERVICE_URL) as channel:
            stub = trip_service_pb2_grpc.TripServiceStub(channel)
            
            # Prepara o pedido com os teus IDs
            request = trip_service_pb2.PassengerCountRequest(trip_ids=trip_ids)
            
            # Faz a chamada e espera pela resposta
            response = stub.GetPassengerCounts(request)
            
            # Devolve o dicionário (map) limpo para usares no teu FastAPI
            return dict(response.trip_passengers)
            
    except grpc.RpcError as e:
        print(f"Erro gRPC ao contactar o Trip Service: {e.details()}")
        return {}