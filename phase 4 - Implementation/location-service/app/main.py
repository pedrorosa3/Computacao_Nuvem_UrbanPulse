from fastapi import FastAPI
from app.routers import uc04_pickup_ranking, uc05_dropoffs, uc06_od_pairs

app = FastAPI(
    title="UrbanPulse — Location Service",
    version="1.0.0",
    description="Historical urban mobility analytics — Location Service",
)

app.include_router(uc04_pickup_ranking.router)
app.include_router(uc05_dropoffs.router)
app.include_router(uc06_od_pairs.router)

@app.get("/health")
def health():
    return {"status": "ok"}