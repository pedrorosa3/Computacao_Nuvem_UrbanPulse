from fastapi import FastAPI
from app.routers import uc19_mobility_comparison, uc18_duration_tip, uc20_anomalous_trips


app = FastAPI(
    title="UrbanPulse — Analytics Service",
    version="1.0.0",
    description="Orchestrator — agrega dados de outros microserviços via gRPC. Sem base de dados própria.",
)

app.include_router(uc18_duration_tip.router)
app.include_router(uc19_mobility_comparison.router)
app.include_router(uc20_anomalous_trips.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "analytics"}
