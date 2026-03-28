from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import uc04_pickup_ranking, uc05_dropoffs, uc06_od_pairs, uc07_zone_profile, uc_zones
from app.grpc_server import serve_grpc


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arrancar o servidor gRPC em background ao iniciar a API
    grpc_server = serve_grpc()
    print("gRPC server started on port 50054")
    yield
    # Parar o servidor gRPC ao desligar
    grpc_server.stop(grace=5)
    print("gRPC server stopped")


app = FastAPI(
    title="UrbanPulse — Location Service",
    version="1.0.0",
    description="Historical urban mobility analytics — Location Service",
    lifespan=lifespan,
)

app.include_router(uc04_pickup_ranking.router)
app.include_router(uc05_dropoffs.router)
app.include_router(uc06_od_pairs.router)
app.include_router(uc07_zone_profile.router)
app.include_router(uc_zones.router)



@app.get("/health")
def health():
    return {"status": "ok"}