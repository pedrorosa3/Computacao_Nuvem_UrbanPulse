from fastapi import APIRouter, Query, HTTPException, Body
from app.database import execute_query, execute_write

router = APIRouter()


@router.delete(
    "/trips/{trip_id}",
    summary="UC21 — Remove a single trip by ID",
    description="Deletes a trip record by its primary key. Returns 404 if not found.",
)
def delete_trip(trip_id: int):
    # Check existence first
    rows = execute_query("SELECT id FROM trips WHERE id = %s", (trip_id,))
    if not rows:
        raise HTTPException(status_code=404, detail=f"Trip {trip_id} not found")

    deleted = execute_write("DELETE FROM trips WHERE id = %s", (trip_id,))
    return {
        "deleted":  True,
        "trip_id":  trip_id,
        "message":  f"Trip {trip_id} successfully deleted.",
    }


@router.delete(
    "/trips/invalid/bulk",
    summary="UC21 — Bulk-remove invalid/suspicious trips",
    description=(
        "Removes all trips that fail basic data-quality checks: zero/negative distance, "
        "zero/negative duration, zero/negative fare, invalid timestamps, or missing zone IDs. "
        "Returns the count of deleted rows. Use dry_run=true to preview without deleting."
    ),
)
def bulk_delete_invalid_trips(
    dry_run: bool = Query(
        False,
        description="If true, count invalid trips without actually deleting them."
    ),
):
    invalid_condition = """
        (
            trip_distance IS NULL OR trip_distance <= 0
            OR fare_amount  IS NULL OR fare_amount  <= 0
            OR trip_duration_min IS NULL OR trip_duration_min <= 0
            OR tpep_dropoff_datetime <= tpep_pickup_datetime
            OR pickup_zone_id  IS NULL
            OR dropoff_zone_id IS NULL
        )
    """

    count_rows = execute_query(
        f"SELECT COUNT(*) AS invalid_count FROM trips WHERE {invalid_condition}"
    )
    invalid_count = int(count_rows[0]["invalid_count"])

    if dry_run:
        return {
            "dry_run":       True,
            "invalid_trips": invalid_count,
            "message":       f"{invalid_count} trips would be deleted (dry_run=true, no changes made).",
            "criteria": [
                "trip_distance IS NULL or ≤ 0",
                "fare_amount IS NULL or ≤ 0",
                "trip_duration_min IS NULL or ≤ 0",
                "dropoff_datetime ≤ pickup_datetime",
                "pickup_zone_id IS NULL",
                "dropoff_zone_id IS NULL",
            ],
        }

    deleted = execute_write(f"DELETE FROM trips WHERE {invalid_condition}")

    return {
        "dry_run":         False,
        "deleted_trips":   deleted,
        "message":         f"{deleted} invalid trips successfully removed from the database.",
        "criteria": [
            "trip_distance IS NULL or ≤ 0",
            "fare_amount IS NULL or ≤ 0",
            "trip_duration_min IS NULL or ≤ 0",
            "dropoff_datetime ≤ pickup_datetime",
            "pickup_zone_id IS NULL",
            "dropoff_zone_id IS NULL",
        ],
    }
