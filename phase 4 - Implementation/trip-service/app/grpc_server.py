import grpc
from concurrent import futures
from app import trip_service_pb2
from app import trip_service_pb2_grpc
from app.database import execute_query


class TripServicer(trip_service_pb2_grpc.TripServiceServicer):
    def GetPassengerCounts(self, request, context):
        trip_ids = list(request.trip_ids)

        if not trip_ids:
            return trip_service_pb2.PassengerCountResponse(trip_passengers={})

        # Busca o passenger_count das viagens pedidas
        placeholders = ",".join(["%s"] * len(trip_ids))
        rows = execute_query(
            f"SELECT id, passenger_count FROM trips WHERE id IN ({placeholders})",
            tuple(trip_ids)
        )

        passengers_map = {
            row["id"]: int(row["passenger_count"])
            for row in rows
            if row["passenger_count"] is not None
        }

        return trip_service_pb2.PassengerCountResponse(trip_passengers=passengers_map)


def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    trip_service_pb2_grpc.add_TripServiceServicer_to_server(TripServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    return server
