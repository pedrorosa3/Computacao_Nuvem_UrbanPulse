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
                    SELECT id AS trip_id, fare_amount, total_amount, tip_amount
                    FROM trips
                    WHERE id = ANY(%s)
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

    def GetZoneGroupRevenue(self, request, context):
        """Calcula avg_fare, avg_tip e avg_tip_pct para um grupo de zonas."""
        zone_ids = list(request.zone_ids)

        if not zone_ids:
            return revenue_service_pb2.ZoneGroupRevenueResponse()

        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    placeholders = ",".join(["%s"] * len(zone_ids))
                    cur.execute(
                        f"""
                        SELECT
                            AVG(fare_amount)                                       AS avg_fare,
                            AVG(tip_amount)                                        AS avg_tip,
                            AVG(CASE WHEN fare_amount > 0
                                THEN tip_amount / fare_amount * 100
                                ELSE NULL END)                                     AS avg_tip_pct
                        FROM trips
                        WHERE pickup_zone_id IN ({placeholders})
                          AND fare_amount > 0
                        """,
                        zone_ids
                    )
                    row = cur.fetchone()

            if not row or row["avg_fare"] is None:
                return revenue_service_pb2.ZoneGroupRevenueResponse()

            return revenue_service_pb2.ZoneGroupRevenueResponse(
                avg_fare=round(float(row["avg_fare"]), 2),
                avg_tip=round(float(row["avg_tip"]), 2),
                avg_tip_pct=round(float(row["avg_tip_pct"]), 2),
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return revenue_service_pb2.ZoneGroupRevenueResponse()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    revenue_service_pb2_grpc.add_RevenueServiceServicer_to_server(
        RevenueServiceServicer(), server
    )
    server.add_insecure_port("[::]:50055")
    server.start()
    print("gRPC Revenue Server started on port 50055")
    return server
