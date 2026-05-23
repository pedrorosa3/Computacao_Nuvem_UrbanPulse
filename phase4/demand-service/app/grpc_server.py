import grpc
import math
from concurrent import futures
from . import demand_service_pb2
from . import demand_service_pb2_grpc
from app.db.connection import get_conn

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
CITY_AVG_CV = 0.8


def _compute_volatility(hourly_counts: dict) -> float:
    counts = [hourly_counts.get(h, 0) for h in range(24)]
    mean = sum(counts) / 24
    if mean == 0:
        return 1.0
    stdev = math.sqrt(sum((c - mean) ** 2 for c in counts) / 24)
    return round((stdev / mean) / CITY_AVG_CV, 2)


def _classify_volatility(v: float) -> str:
    if v < 0.5:  return "low"
    if v <= 1.5: return "medium"
    return "high"


class DemandServicer(demand_service_pb2_grpc.DemandServiceServicer):

    def GetZoneHourlyDemand(self, request, context):
        hourly_query = """
            SELECT pickup_hour AS hour, COUNT(*) AS trip_count
            FROM trips WHERE pickup_zone_id = %s
            GROUP BY pickup_hour
        """
        day_query = """
            SELECT pickup_day_of_week, COUNT(*) AS cnt
            FROM trips WHERE pickup_zone_id = %s
            GROUP BY pickup_day_of_week ORDER BY cnt DESC LIMIT 1
        """
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(hourly_query, [request.zone_id])
                    rows = cur.fetchall()
                    counts_map = {int(r["hour"]): int(r["trip_count"]) for r in rows}
                    cur.execute(day_query, [request.zone_id])
                    day_row = cur.fetchone()
                    peak_day = DAY_NAMES[int(day_row["pickup_day_of_week"])] if day_row else ""
            return demand_service_pb2.ZoneDemandResponse(
                hourly_counts=counts_map,
                peak_day=peak_day
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return demand_service_pb2.ZoneDemandResponse()

    def GetGroupDemand(self, request, context):
        """Calcula volatility e peak_hour agregados para um grupo de zonas."""
        zone_ids = list(request.zone_ids)
        if not zone_ids:
            return demand_service_pb2.GroupDemandResponse()

        try:
            placeholders = ",".join(["%s"] * len(zone_ids))
            query = f"""
                SELECT pickup_hour AS hour, COUNT(*) AS trip_count
                FROM trips
                WHERE pickup_zone_id IN ({placeholders})
                GROUP BY pickup_hour
            """
            peak_query = f"""
                SELECT pickup_hour, COUNT(*) AS cnt
                FROM trips
                WHERE pickup_zone_id IN ({placeholders})
                GROUP BY pickup_hour ORDER BY cnt DESC LIMIT 1
            """
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, zone_ids)
                    rows = cur.fetchall()
                    counts_map = {int(r["hour"]): int(r["trip_count"]) for r in rows}
                    cur.execute(peak_query, zone_ids)
                    peak_row = cur.fetchone()
                    peak_hour = int(peak_row["pickup_hour"]) if peak_row else 0

            volatility = _compute_volatility(counts_map)
            return demand_service_pb2.GroupDemandResponse(
                peak_hour=peak_hour,
                avg_volatility_index=volatility,
                volatility_classification=_classify_volatility(volatility),
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return demand_service_pb2.GroupDemandResponse()


def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    demand_service_pb2_grpc.add_DemandServiceServicer_to_server(DemandServicer(), server)
    server.add_insecure_port('[::]:50053')
    server.start()
    return server