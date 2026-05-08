from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.routers import uc19_mobility_comparison, uc18_duration_tip, uc20_anomalous_trips


app = FastAPI(
    docs_url="/analytics/docs",
    openapi_url="/analytics/openapi.json",
    title="UrbanPulse — Analytics Service",
    version="1.0.0",
    description="Orchestrator — agrega dados de outros microserviços via gRPC. Sem base de dados própria.",
)

app.include_router(uc18_duration_tip.router)
app.include_router(uc19_mobility_comparison.router)
app.include_router(uc20_anomalous_trips.router)

Instrumentator().instrument(app).expose(app, endpoint="/analytics/metrics", include_in_schema=False)

@app.get("/analytics/health")
def health():
    return {"status": "ok", "service": "analytics"}

@app.get("/health")
def health_root():
    return {"status": "ok", "service": "analytics"}