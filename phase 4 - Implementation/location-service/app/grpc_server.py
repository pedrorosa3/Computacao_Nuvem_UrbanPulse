import grpc
from concurrent import futures
from . import location_service_pb2
from . import location_service_pb2_grpc
from app.database import execute_query


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
            print(f"Erro no gRPC (Location Service): {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return location_service_pb2.ZoneNameResponse()


def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10)) #Podemos aumentar este valor, tendo em conta quantos pedidos queremos responder em simultaneo
    location_service_pb2_grpc.add_LocationServiceServicer_to_server(LocationServicer(), server)
    server.add_insecure_port("[::]:50054")
    server.start()
    return server