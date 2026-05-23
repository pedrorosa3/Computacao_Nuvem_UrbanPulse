from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import hourly_matrix, monthly_trend, volatility
from app.grpc_server import serve_grpc

grpc_server_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global grpc_server_instance
    grpc_server_instance = serve_grpc()
    print("Demand Service gRPC na porta 50053!")
    yield
    grpc_server_instance.stop(0)

app = FastAPI(
    docs_url="/demand/docs",
    openapi_url="/demand/openapi.json",
    title="UrbanPulse – Demand Service API",
    description="Historical demand analysis of NYC Yellow Taxi trip data.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(hourly_matrix.router,  prefix="/demand")
app.include_router(monthly_trend.router,  prefix="/demand")
app.include_router(volatility.router,     prefix="/demand") # O teu UC17!

@app.get("/health")
def health():
    return {"status": "ok", "service": "demand"}