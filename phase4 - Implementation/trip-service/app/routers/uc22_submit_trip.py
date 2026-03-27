from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from app.database import execute_write_returning

router = APIRouter()


class TripSubmission(BaseModel):
    tpep_pickup_datetime:  datetime = Field(..., description="Pickup timestamp (ISO 8601)")
    tpep_dropoff_datetime: datetime = Field(..., description="Drop-off timestamp (ISO 8601)")
    passenger_count:       int      = Field(..., ge=1, le=9,  description="Number of passengers (1–9)")
    trip_distance:         float    = Field(..., gt=0,         description="Trip distance in miles (> 0)")
    pickup_zone_id:        int      = Field(..., ge=1,         description="Pickup zone location ID")
    pickup_zone_name:      str      = Field(..., min_length=1, description="Pickup zone name")
    dropoff_zone_id:       int      = Field(..., ge=1,         description="Drop-off zone location ID")
    dropoff_zone_name:     str      = Field(..., min_length=1, description="Drop-off zone name")
    fare_amount:           float    = Field(..., gt=0,         description="Base fare in USD (> 0)")
    tip_amount:            float    = Field(0.0, ge=0,         description="Tip in USD (≥ 0)")
    total_amount:          float    = Field(..., gt=0,         description="Total charged in USD (> 0)")
    payment_type:          int      = Field(..., ge=1, le=6,   description="Payment type (1=Credit, 2=Cash, ...)")

    @field_validator("tpep_dropoff_datetime")
    @classmethod
    def dropoff_after_pickup(cls, dropoff, info):
        pickup = info.data.get("tpep_pickup_datetime")
        if pickup and dropoff <= pickup:
            raise ValueError("dropoff datetime must be after pickup datetime")
        return dropoff

    @field_validator("total_amount")
    @classmethod
    def total_at_least_fare(cls, total, info):
        fare = info.data.get("fare_amount")
        tip  = info.data.get("tip_amount", 0.0)
        if fare and total < fare:
            raise ValueError("total_amount must be ≥ fare_amount")
        return total


@router.post(
    "/trips",
    status_code=201,
    summary="UC22 — Submit a new trip",
    description=(
        "Submits a new taxi trip record for storage and analysis. "
        "Validates all fields including temporal consistency and fare logic. "
        "Returns the created trip with its assigned ID and computed duration."
    ),
)
def submit_trip(trip: TripSubmission):
    duration_min = (
        trip.tpep_dropoff_datetime - trip.tpep_pickup_datetime
    ).total_seconds() / 60.0

    row = execute_write_returning(
        """
        INSERT INTO trips (
            tpep_pickup_datetime, tpep_dropoff_datetime,
            passenger_count, trip_distance,
            pickup_zone_id, pickup_zone_name,
            dropoff_zone_id, dropoff_zone_name,
            fare_amount, tip_amount, total_amount,
            payment_type, trip_duration_min
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id
        """,
        (
            trip.tpep_pickup_datetime,
            trip.tpep_dropoff_datetime,
            trip.passenger_count,
            trip.trip_distance,
            trip.pickup_zone_id,
            trip.pickup_zone_name,
            trip.dropoff_zone_id,
            trip.dropoff_zone_name,
            trip.fare_amount,
            trip.tip_amount,
            trip.total_amount,
            trip.payment_type,
            round(duration_min, 2),
        ),
    )

    if not row:
        raise HTTPException(status_code=500, detail="Failed to insert trip")

    trip_id = row["id"]

    return {
        "trip_id":              trip_id,
        "message":              "Trip successfully submitted.",
        "tpep_pickup_datetime":  str(trip.tpep_pickup_datetime),
        "tpep_dropoff_datetime": str(trip.tpep_dropoff_datetime),
        "trip_duration_min":    round(duration_min, 2),
        "passenger_count":      trip.passenger_count,
        "trip_distance_mi":     trip.trip_distance,
        "pickup_zone_id":       trip.pickup_zone_id,
        "pickup_zone_name":     trip.pickup_zone_name,
        "dropoff_zone_id":      trip.dropoff_zone_id,
        "dropoff_zone_name":    trip.dropoff_zone_name,
        "fare_amount":          trip.fare_amount,
        "tip_amount":           trip.tip_amount,
        "total_amount":         trip.total_amount,
        "payment_type":         trip.payment_type,
    }
