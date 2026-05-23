from fastapi import FastAPI
from app.routers import hourly_matrix, monthly_trend

app = FastAPI(
    title="UrbanPulse – Demand Service API",
    description="Historical demand analysis of NYC Yellow Taxi trip data.",
    version="1.0.0",
)

app.include_router(hourly_matrix.router,  prefix="/demand")
app.include_router(monthly_trend.router,  prefix="/demand")


@app.get("/health")
def health():
    return {"status": "ok", "service": "demand"}
