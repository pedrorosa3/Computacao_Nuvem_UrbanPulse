from fastapi import APIRouter
from app.database import execute_query

router = APIRouter()

# Classificação fixa server-side (conforme spec UC19)
AFFLUENT_SERVICE_ZONES   = {"Yellow Zone"}
PERIPHERAL_BOROUGHS      = {"Bronx", "Staten Island"}
PERIPHERAL_SERVICE_ZONES = {"Boro Zone"}


def classify_zone(borough: str, service_zone: str) -> str:
    if service_zone in AFFLUENT_SERVICE_ZONES:
        return "affluent"
    if borough in PERIPHERAL_BOROUGHS or service_zone in PERIPHERAL_SERVICE_ZONES:
        return "peripheral"
    return "other"


@router.get("/locations/zones")
def get_all_zones():
    """
    Devolve todas as zonas com a sua classificação (affluent / peripheral / other).
    Usado internamente pelo Analytics Service para o UC19.
    """
    rows = execute_query(
        "SELECT location_id, zone_name, borough, service_zone FROM zones ORDER BY location_id"
    )
    return [
        {
            "zone_id":        row["location_id"],
            "zone_name":      row["zone_name"],
            "borough":        row["borough"],
            "service_zone":   row["service_zone"],
            "classification": classify_zone(row["borough"], row["service_zone"]),
        }
        for row in rows
    ]