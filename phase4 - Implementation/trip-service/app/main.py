from fastapi import FastAPI
from app.routers import (
    uc01_time_of_day,
    uc02_route_deviation,
    uc03_speed_zones,
    uc18_duration_tip,
    uc20_suspicious,
    uc21_remove_invalid,
    uc22_submit_trip,
)

app = FastAPI(
    title="UrbanPulse — Trip Service",
    version="1.0.0",
    description=(
        "Historical urban mobility analytics — Trip Service. "
        "Provides trip intelligence including time-of-day classification, "
        "route deviation analysis, speed analytics, and data quality management."
    ),
)

app.include_router(uc01_time_of_day.router)
app.include_router(uc02_route_deviation.router)
app.include_router(uc03_speed_zones.router)
app.include_router(uc18_duration_tip.router)
app.include_router(uc20_suspicious.router)
app.include_router(uc21_remove_invalid.router)
app.include_router(uc22_submit_trip.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "trip-service"}
