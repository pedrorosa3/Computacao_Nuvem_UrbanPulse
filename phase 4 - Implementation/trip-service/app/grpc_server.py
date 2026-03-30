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
    
    def GetDistanceByZone(self, request, context): #UC 10
        zone_type = request.zone_type if request.zone_type in ("pickup", "dropoff") else "pickup"
        zone_col = f"{zone_type}_zone_id"
 
        conditions = ["trip_distance_km > 0"]
        params     = []
 
        if request.year and request.year > 0:
            conditions.append("EXTRACT(YEAR  FROM pickup_datetime) = %s")
            params.append(request.year)
 
        if request.month and request.month > 0:
            conditions.append("EXTRACT(MONTH FROM pickup_datetime) = %s")
            params.append(request.month)
 
        where = " AND ".join(conditions)
 
        query = f"""
            SELECT
                {zone_col}         AS zone_id,
                AVG(trip_distance_km)  AS avg_distance,
                COUNT(*)           AS trip_count
            FROM trips
            WHERE {where}
            GROUP BY {zone_col}
        """
 
        try:
            rows = execute_query(query, tuple(params))
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"DB error: {e}")
            return trip_service_pb2.DistanceByZoneResponse()
 
        zones = [
            trip_service_pb2.ZoneDistanceInfo(
                zone_id=int(row["zone_id"]),
                avg_distance=float(row["avg_distance"]),
                trip_count=int(row["trip_count"]),
            )
            for row in rows
        ]
 
        return trip_service_pb2.DistanceByZoneResponse(zones=zones)


def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    trip_service_pb2_grpc.add_TripServiceServicer_to_server(TripServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    return server
