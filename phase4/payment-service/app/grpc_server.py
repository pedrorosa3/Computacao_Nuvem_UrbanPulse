import grpc
from concurrent import futures
from . import payment_service_pb2
from . import payment_service_pb2_grpc
from .database import SessionLocal
from .models import Trip

# Esta classe implementa o contrato que definiste no ficheiro .proto
class PaymentServicer(payment_service_pb2_grpc.PaymentServiceServicer):
    
    def GetPaymentDetails(self, request, context):
        # Abrimos uma ligação à base de dados só para este pedido
        db = SessionLocal()
        try:
            payments_map = {}
            # Vamos buscar à DB todas as viagens cujos IDs vieram no pedido
            trips = db.query(Trip).filter(Trip.id.in_(request.trip_ids)).all()
            
            for t in trips:
                payments_map[t.id] = payment_service_pb2.TripPaymentInfo(
                    fare_amount=t.fare_amount,
                    tip_amount=t.tip_amount,
                    payment_type=t.payment_type
                )
                
            return payment_service_pb2.PaymentResponse(payments=payments_map)
        finally:
            db.close() # Fechamos a ligação para não esgotar a memória

# Função que liga o servidor
def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    payment_service_pb2_grpc.add_PaymentServiceServicer_to_server(PaymentServicer(), server)
    
    # É aqui que defines a TUA porta!
    server.add_insecure_port('[::]:50052') 
    server.start()
    return server