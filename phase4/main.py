from fastapi import FastAPI
from app.routers import avg_fare, breakdown, fare_per_km

app = FastAPI(
    title="UrbanPulse – Revenue & Pricing Intelligence API",
    description="Historical revenue and pricing analysis of NYC Yellow Taxi trip data.",
    version="1.0.0",
)

app.include_router(avg_fare.router,    prefix="/revenue")
app.include_router(breakdown.router,   prefix="/revenue")
app.include_router(fare_per_km.router, prefix="/revenue")


@app.get("/health")
def health():
    return {"status": "ok", "service": "revenue"}
