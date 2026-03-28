import grpc
from concurrent import futures
from . import demand_service_pb2
from . import demand_service_pb2_grpc
from app.db.connection import get_conn

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class DemandServicer(demand_service_pb2_grpc.DemandServiceServicer):

    def GetZoneHourlyDemand(self, request, context):
        hourly_query = """
            SELECT pickup_hour AS hour, COUNT(*) AS trip_count
            FROM trips
            WHERE pickup_zone_id = %s
            GROUP BY pickup_hour
        """
        day_query = """
            SELECT pickup_day_of_week, COUNT(*) AS cnt
            FROM trips
            WHERE pickup_zone_id = %s
            GROUP BY pickup_day_of_week
            ORDER BY cnt DESC
            LIMIT 1
        """

        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    # Hourly counts
                    cur.execute(hourly_query, [request.zone_id])
                    rows = cur.fetchall()
                    counts_map = {int(r["hour"]): int(r["trip_count"]) for r in rows}

                    # Peak day
                    cur.execute(day_query, [request.zone_id])
                    day_row = cur.fetchone()
                    peak_day = DAY_NAMES[int(day_row["pickup_day_of_week"])] if day_row else ""

            return demand_service_pb2.ZoneDemandResponse(
                hourly_counts=counts_map,
                peak_day=peak_day
            )

        except Exception as e:
            print(f"Erro na BD do Demand Service (gRPC): {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return demand_service_pb2.ZoneDemandResponse()


def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    demand_service_pb2_grpc.add_DemandServiceServicer_to_server(DemandServicer(), server)
    server.add_insecure_port('[::]:50053')
    server.start()
    return server