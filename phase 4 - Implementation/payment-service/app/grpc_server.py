import grpc
from concurrent import futures
from . import payment_service_pb2
from . import payment_service_pb2_grpc
from .database import SessionLocal
from .models import Trip
from sqlalchemy import func


class PaymentServicer(payment_service_pb2_grpc.PaymentServiceServicer):

    def GetPaymentDetails(self, request, context):
        db = SessionLocal()
        try:
            payments_map = {}
            trips = db.query(Trip).filter(Trip.id.in_(request.trip_ids)).all()
            for t in trips:
                payments_map[t.id] = payment_service_pb2.TripPaymentInfo(
                    fare_amount=t.fare_amount,
                    tip_amount=t.tip_amount,
                    payment_type=t.payment_type
                )
            return payment_service_pb2.PaymentResponse(payments=payments_map)
        finally:
            db.close()

    def GetPaymentDistribution(self, request, context):
        """Devolve a percentagem de pagamentos card vs cash."""
        db = SessionLocal()
        try:
            query = db.query(
                Trip.payment_type,
                func.count(Trip.id).label("cnt")
            )
            if request.start_date:
                query = query.filter(Trip.pickup_date >= request.start_date)
            if request.end_date:
                query = query.filter(Trip.pickup_date <= request.end_date)

            results = query.group_by(Trip.payment_type).all()

            total = sum(r.cnt for r in results)
            dist = {r.payment_type: r.cnt for r in results}

            card_pct = round(dist.get("card", 0) * 100.0 / total, 2) if total else 0.0
            cash_pct = round(dist.get("cash", 0) * 100.0 / total, 2) if total else 0.0

            return payment_service_pb2.PaymentDistributionResponse(
                card_payment_pct=card_pct,
                cash_payment_pct=cash_pct,
            )
        finally:
            db.close()


def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    payment_service_pb2_grpc.add_PaymentServiceServicer_to_server(PaymentServicer(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    return server
