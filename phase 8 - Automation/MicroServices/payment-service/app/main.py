from contextlib import asynccontextmanager
from fastapi import FastAPI
from .grpc_server import serve_grpc
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from prometheus_fastapi_instrumentator import Instrumentator

grpc_server_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global grpc_server_instance
    grpc_server_instance = serve_grpc()
    print("🚀 Servidor gRPC do Payment Service a correr na porta 50052!")

    redis = aioredis.from_url("redis://redis:6379")
    FastAPICache.init(RedisBackend(redis), prefix="payment-cache")
    print("🚀 Cache Redis inicializada com sucesso!")

    yield

    grpc_server_instance.stop(0)
    print("🛑 Servidor gRPC desligado.")


app = FastAPI(
    docs_url="/payments/docs",
    openapi_url="/payments/openapi.json",
    title="Payment Service API - UrbanPulse",
    description="API do microserviço de pagamentos desenvolvida por Pedro Rosa.",
    version="1.0.0",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, endpoint="/payments/metrics", include_in_schema=False)


@app.get("/")
def root_health():
    return {"status": "ok", "message": "Payment Service Root is alive!"}


@app.get("/health")
async def health_root():
    return {"status": "ok", "service": "payment-service"}


@app.get("/payments/health")
async def health_payments():
    return {"status": "ok", "service": "payment-service"}
