from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/fare-per-km", summary="UC10 – Fare per km by zone")
def fare_per_km():
    # TODO: implementar quando a integração com o Trip Service via gRPC estiver disponível.
    # Este endpoint requer trip_distance_km que pertence ao Trip Service.
    raise HTTPException(
        status_code=501,
        detail="Not implemented: requires Trip Service integration via gRPC."
    )