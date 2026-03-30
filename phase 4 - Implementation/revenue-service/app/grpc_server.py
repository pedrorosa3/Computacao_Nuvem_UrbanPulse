import grpc
from concurrent import futures
from app import revenue_service_pb2, revenue_service_pb2_grpc
from app.db.connection import get_conn

class RevenueServiceServicer(revenue_service_pb2_grpc.RevenueServiceServicer):
    def GetTripRevenues(self, request, context):
        trip_ids = list(request.trip_ids)

        if not trip_ids:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("No trip_ids provided")
            return revenue_service_pb2.TripRevenueResponse()

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT trip_id, fare_amount, total_amount, tip_amount
                    FROM trips
                    WHERE trip_id = ANY(%s)
                    """,
                    (trip_ids,)
                )
                rows = cur.fetchall()

        revenues = [
            revenue_service_pb2.TripRevenueInfo(
                trip_id=row["trip_id"],
                fare_amount=float(row["fare_amount"] or 0),
                total_amount=float(row["total_amount"] or 0),
                tip_amount=float(row["tip_amount"] or 0),
            )
            for row in rows
        ]

        return revenue_service_pb2.TripRevenueResponse(revenues=revenues)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    revenue_service_pb2_grpc.add_RevenueServiceServicer_to_server(
        RevenueServiceServicer(), server
    )
    server.add_insecure_port("[::]:50055")
    server.start()
    print("gRPC Revenue Server started on port 50055")
    return server
