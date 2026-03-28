from fastapi import FastAPI
from app.routers import (
    uc01_time_of_day,
    uc02_route_deviation,
    uc03_speed_zones,
    uc21_remove_invalid,
    uc22_submit_trip,
)

app = FastAPI(
    title="UrbanPulse — Trip Service",
    version="1.0.0",
    description=(
        "Historical urban mobility analytics — Trip Service. "
        "UC01: Time-of-day classification | "
        "UC02: Route deviation index | "
        "UC03: Speed by zone | "
        "UC21: Data quality management | "
        "UC22: Trip submission"
    ),
)

app.include_router(uc01_time_of_day.router)
app.include_router(uc02_route_deviation.router)
app.include_router(uc03_speed_zones.router)
app.include_router(uc21_remove_invalid.router)
app.include_router(uc22_submit_trip.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "trip-service"}
