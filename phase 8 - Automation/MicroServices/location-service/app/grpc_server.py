import grpc
from concurrent import futures
from . import location_service_pb2
from . import location_service_pb2_grpc
from app.database import execute_query

AFFLUENT_SERVICE_ZONES   = {"Yellow Zone"}
PERIPHERAL_BOROUGHS      = {"Bronx", "Staten Island"}
PERIPHERAL_SERVICE_ZONES = {"Boro Zone"}


def classify_zone(borough: str, service_zone: str) -> str:
    if service_zone in AFFLUENT_SERVICE_ZONES:
        return "affluent"
    if borough in PERIPHERAL_BOROUGHS or service_zone in PERIPHERAL_SERVICE_ZONES:
        return "peripheral"
    return "other"


class LocationServicer(location_service_pb2_grpc.LocationServiceServicer):

    def GetZoneName(self, request, context):
        try:
            rows = execute_query(
                "SELECT zone_name, borough FROM zones WHERE location_id = %s",
                (request.zone_id,)
            )
            if not rows:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Zone {request.zone_id} not found")
                return location_service_pb2.ZoneNameResponse()
            return location_service_pb2.ZoneNameResponse(
                zone_name=rows[0]["zone_name"],
                borough=rows[0]["borough"],
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return location_service_pb2.ZoneNameResponse()

    def GetZoneNames(self, request, context):
        """UC08 — Batch lookup de nomes de zonas para o Revenue Service."""
        zone_ids = list(request.zone_ids)
        if not zone_ids:
            return location_service_pb2.ZoneNamesResponse()

        try:
            placeholders = ",".join(["%s"] * len(zone_ids))
            rows = execute_query(
                f"SELECT location_id, zone_name, borough FROM zones WHERE location_id IN ({placeholders})",
                tuple(zone_ids)
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return location_service_pb2.ZoneNamesResponse()

        zones = [
            location_service_pb2.ZoneNameInfo(
                zone_id=row["location_id"],
                zone_name=row["zone_name"],
                borough=row["borough"],
            )
            for row in rows
        ]
        return location_service_pb2.ZoneNamesResponse(zones=zones)

    def GetZoneGroups(self, request, context):
        try:
            zones = execute_query(
                "SELECT location_id, borough, service_zone FROM zones"
            )

            affluent_ids   = [z["location_id"] for z in zones if classify_zone(z["borough"], z["service_zone"]) == "affluent"]
            peripheral_ids = [z["location_id"] for z in zones if classify_zone(z["borough"], z["service_zone"]) == "peripheral"]

            filters, params = [], []
            if request.start_date:
                filters.append("pickup_date >= %s")
                params.append(request.start_date)
            if request.end_date:
                filters.append("pickup_date <= %s")
                params.append(request.end_date)
            date_where = (" AND " + " AND ".join(filters)) if filters else ""

            total_rows  = execute_query(
                f"SELECT COUNT(*) AS total FROM trips WHERE 1=1{date_where}",
                tuple(params)
            )
            total_trips = total_rows[0]["total"] if total_rows else 0

            def group_trips(zone_ids):
                if not zone_ids:
                    return 0
                placeholders = ",".join(["%s"] * len(zone_ids))
                rows = execute_query(
                    f"SELECT COUNT(*) AS total FROM trips WHERE pickup_zone_id IN ({placeholders}){date_where}",
                    tuple(zone_ids) + tuple(params)
                )
                return rows[0]["total"] if rows else 0

            affluent_trips   = group_trips(affluent_ids)
            peripheral_trips = group_trips(peripheral_ids)

            def market_share(trips):
                return round(trips * 100.0 / total_trips, 2) if total_trips else 0.0

            return location_service_pb2.ZoneGroupsResponse(
                total_trips=total_trips,
                affluent=location_service_pb2.ZoneGroup(
                    zone_count=len(affluent_ids),
                    total_trips=affluent_trips,
                    market_share_pct=market_share(affluent_trips),
                    zone_ids=affluent_ids,
                ),
                peripheral=location_service_pb2.ZoneGroup(
                    zone_count=len(peripheral_ids),
                    total_trips=peripheral_trips,
                    market_share_pct=market_share(peripheral_trips),
                    zone_ids=peripheral_ids,
                ),
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return location_service_pb2.ZoneGroupsResponse()


def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    location_service_pb2_grpc.add_LocationServiceServicer_to_server(LocationServicer(), server)
    server.add_insecure_port("[::]:50054")
    server.start()
    return server
