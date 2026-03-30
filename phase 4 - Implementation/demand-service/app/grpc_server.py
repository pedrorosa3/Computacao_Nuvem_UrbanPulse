import grpc
from concurrent import futures
from . import demand_service_pb2
from . import demand_service_pb2_grpc
from app.db.connection import get_conn # A função de BD do Francisco!

class DemandServicer(demand_service_pb2_grpc.DemandServiceServicer):
    
    def GetZoneHourlyDemand(self, request, context):
        query = """
            SELECT pickup_hour AS hour, COUNT(*) AS trip_count
            FROM trips
            WHERE pickup_zone_id = %s
            GROUP BY pickup_hour
        """
        
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, [request.zone_id])
                    rows = cur.fetchall()
            
            # Converter o resultado (lista de dicionários) para um dicionário simples {hora: contagem}
            counts_map = {int(r["hour"]): int(r["trip_count"]) for r in rows}
            
            return demand_service_pb2.ZoneDemandResponse(hourly_counts=counts_map)
            
        except Exception as e:
            print(f"Erro na BD do Demand Service (gRPC): {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return demand_service_pb2.ZoneDemandResponse()

def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    demand_service_pb2_grpc.add_DemandServiceServicer_to_server(DemandServicer(), server)
    
    # Vamos usar a porta 50053 para o Demand Service!
    server.add_insecure_port('[::]:50053') 
    server.start()
    return server