from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from app.database import execute_write_returning

router = APIRouter()

MILES_TO_KM     = 1.60934
REFERENCE_SPEED = 12.0
SLOW_KMH        = 15.0
FAST_KMH        = 30.0
PAYMENT_MAP     = {1: "card", 2: "cash", 3: "no_charge", 4: "dispute"}


def _time_class(dt: datetime) -> str:
    h = dt.hour
    if 7 <= h <= 9 or 16 <= h <= 19:
        return "peak"
    elif h >= 22 or h < 6:
        return "night"
    return "off_peak"


def _deviation(distance_mi: float, duration_min: float):
    if distance_mi <= 0 or duration_min <= 0:
        return None, None
    rdi = duration_min / ((distance_mi / REFERENCE_SPEED) * 60)
    cls = "efficient" if rdi <= 1.20 else ("moderate" if rdi <= 1.60 else "inefficient")
    return round(rdi, 4), cls


def _speed(distance_mi: float, duration_min: float):
    if distance_mi <= 0 or duration_min <= 0:
        return None, None
    s = (distance_mi * MILES_TO_KM) / (duration_min / 60.0)
    if s >= 200:
        return None, None
    cls = "slow" if s < SLOW_KMH else ("normal" if s <= FAST_KMH else "fast")
    return round(s, 2), cls


class TripSubmission(BaseModel):
    pickup_datetime:  datetime = Field(..., description="Pickup timestamp (ISO 8601)")
    dropoff_datetime: datetime = Field(..., description="Drop-off timestamp (ISO 8601)")
    passenger_count:  int      = Field(..., ge=1, le=9)
    trip_distance_km: float    = Field(..., gt=0, description="Trip distance in km")
    pickup_zone_id:   int      = Field(..., ge=1)
    pickup_zone_name: str      = Field(..., min_length=1)
    dropoff_zone_id:  int      = Field(..., ge=1)
    dropoff_zone_name: str     = Field(..., min_length=1)
    fare_amount:      float    = Field(..., gt=0)
    tip_amount:       float    = Field(0.0, ge=0)
    payment_type:     int      = Field(..., ge=1, le=4, description="1=card 2=cash 3=no_charge 4=dispute")

    @field_validator("dropoff_datetime")
    @classmethod
    def dropoff_after_pickup(cls, dropoff, info):
        pickup = info.data.get("pickup_datetime")
        if pickup and dropoff <= pickup:
            raise ValueError("dropoff_datetime must be after pickup_datetime")
        return dropoff


@router.post(
    "/trips",
    status_code=201,
    summary="UC22 — Submit a new trip",
    description=(
        "Inserts a new trip with all enriched columns automatically computed "
        "(time_class, deviation_index, deviation_class, avg_speed_kmh, speed_class, suspicion_score)."
    ),
)
def submit_trip(trip: TripSubmission):
    duration_min  = (trip.dropoff_datetime - trip.pickup_datetime).total_seconds() / 60.0
    distance_mi   = trip.trip_distance_km / MILES_TO_KM

    time_class              = _time_class(trip.pickup_datetime)
    deviation_index, dev_class = _deviation(distance_mi, duration_min)
    avg_speed_kmh, spd_class   = _speed(distance_mi, duration_min)
    payment_str             = PAYMENT_MAP.get(trip.payment_type, "unknown")

    # Simple suspicion check on submitted trip
    suspicion_score = 0
    if trip.trip_distance_km < 3.2 and trip.fare_amount > 30:
        suspicion_score += 1
    if avg_speed_kmh and avg_speed_kmh > 160:
        suspicion_score += 1
    if trip.tip_amount > trip.fare_amount * 2:
        suspicion_score += 1

    row = execute_write_returning(
        """
        INSERT INTO trips (
            pickup_datetime, dropoff_datetime,
            pickup_zone_id, dropoff_zone_id,
            pickup_zone_name, dropoff_zone_name,
            trip_distance_km, fare_amount, tip_amount,
            passenger_count, payment_type,
            time_class, deviation_index, deviation_class,
            avg_speed_kmh, speed_class, suspicion_score
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        ) RETURNING id
        """,
        (
            trip.pickup_datetime, trip.dropoff_datetime,
            trip.pickup_zone_id, trip.dropoff_zone_id,
            trip.pickup_zone_name, trip.dropoff_zone_name,
            trip.trip_distance_km, trip.fare_amount, trip.tip_amount,
            trip.passenger_count, payment_str,
            time_class, deviation_index, dev_class,
            avg_speed_kmh, spd_class, suspicion_score,
        ),
    )

    if not row:
        raise HTTPException(status_code=500, detail="Failed to insert trip")

    return {
        "trip_id":          row["id"],
        "message":          "Trip successfully submitted.",
        "pickup_datetime":  str(trip.pickup_datetime),
        "dropoff_datetime": str(trip.dropoff_datetime),
        "duration_min":     round(duration_min, 2),
        "trip_distance_km": trip.trip_distance_km,
        "fare_amount":      trip.fare_amount,
        "tip_amount":       trip.tip_amount,
        "payment_type":     payment_str,
        "enriched": {
            "time_class":       time_class,
            "deviation_index":  deviation_index,
            "deviation_class":  dev_class,
            "avg_speed_kmh":    avg_speed_kmh,
            "speed_class":      spd_class,
            "suspicion_score":  suspicion_score,
        },
    }
