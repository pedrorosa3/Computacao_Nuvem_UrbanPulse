from contextlib import asynccontextmanager
from fastapi import FastAPI
from .routers import payments
from .grpc_server import serve_grpc
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis
from prometheus_fastapi_instrumentator import Instrumentator

grpc_server_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # O que acontece ao LIGAR a API:
    global grpc_server_instance
    grpc_server_instance = serve_grpc()
    print("🚀 Servidor gRPC do Payment Service a correr na porta 50052!")
    
    # INICIALIZAR O REDIS AQUI DENTRO!
    redis = aioredis.from_url("redis://redis-service:6379")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    print("🚀 Cache Redis inicializada com sucesso!")
    
    yield
    
    # O que acontece ao DESLIGAR a API:
    grpc_server_instance.stop(0)
    print("🛑 Servidor gRPC desligado.")

app = FastAPI(
    docs_url="/payments/docs",
    openapi_url="/payments/openapi.json",
    title="Payment Service API - UrbanPulse",
    description="API do microserviço de pagamentos desenvolvida por Pedro Rosa.",
    version="1.0.0",
    lifespan=lifespan # Agora o lifespan arranca o gRPC e o Redis!
)

# Inicializar o Prometheus
Instrumentator().instrument(app).expose(app)

app.include_router(payments.router, prefix="/payments", tags=["Payments"])


@app.get("/")
def root_health():
    """Endpoint vitalício para o Ingress (Load Balancer) do GKE saber que estamos vivos."""
    return {"status": "ok", "message": "Payment Service Root is alive!"}

#Endpoints de Health (com nomes de função diferentes para não dar conflito)
@app.get("/health")

async def health_root():
    return {"status": "ok", "service": "payment-service"}

@app.get("/payments/health")

async def health_payments():
    return {"status": "ok", "service": "payment-service"}