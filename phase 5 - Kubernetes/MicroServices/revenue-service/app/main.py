import threading
from fastapi import FastAPI
from app.routers import avg_fare, breakdown, fare_per_km
from app.grpc_server import serve as grpc_serve

app = FastAPI(
    docs_url="/revenue/docs",
    openapi_url="/revenue/openapi.json",
    title="UrbanPulse – Revenue & Pricing Intelligence API",
    description="Historical revenue and pricing analysis of NYC Yellow Taxi trip data.",
    version="1.0.0",
)

app.include_router(avg_fare.router,    prefix="/revenue")
app.include_router(breakdown.router,   prefix="/revenue")
app.include_router(fare_per_km.router, prefix="/revenue")


@app.on_event("startup")
def startup_grpc():
    grpc_server = grpc_serve()
    t = threading.Thread(target=grpc_server.wait_for_termination, daemon=True)
    t.start()

@app.get("/health")
def health():
    return {"status": "ok", "service": "revenue"}


@app.get("/revenue/health")
def health():
    return {"status": "ok", "service": "revenue"}
