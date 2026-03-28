from contextlib import asynccontextmanager
from fastapi import FastAPI
from .routers import payments
from .grpc_server import serve_grpc

grpc_server_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # O que acontece ao LIGAR a API:
    global grpc_server_instance
    grpc_server_instance = serve_grpc()
    print("🚀 Servidor gRPC do Payment Service a correr na porta 50052!")
    yield
    # O que acontece ao DESLIGAR a API:
    grpc_server_instance.stop(0)
    print("🛑 Servidor gRPC desligado.")

app = FastAPI(
    title="Payment Service API - UrbanPulse",
    description="API do microserviço de pagamentos desenvolvida por Pedro Rosa.",
    version="1.0.0",
    lifespan=lifespan # Dizemos ao FastAPI para usar a função que gere o gRPC
)

app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])

@app.get("/")
def root():
    return {"message": "Payment Service está online!"}