from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from app.database import execute_query, execute_write, execute_write_returning

router = APIRouter()


@router.delete(
    "/trips/invalid/bulk",
    summary="UC21 — Bulk-remove invalid trips",
    description=(
        "Removes trips that fail basic data-quality checks and logs each deletion. "
        "Use dry_run=true to preview without deleting."
    ),
)
def bulk_delete_invalid_trips(
    dry_run: bool = Query(False, description="Preview without deleting if true"),
):
    invalid_condition = """
        (
            trip_distance_km IS NULL OR trip_distance_km <= 0
            OR fare_amount   IS NULL OR fare_amount   <= 0
            OR dropoff_datetime <= pickup_datetime
            OR pickup_zone_id   IS NULL
            OR dropoff_zone_id  IS NULL
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
        }

    # Log before deleting
    execute_write(
        f"""
        INSERT INTO audit_log (trip_id, reason)
        SELECT id, 'Bulk removal — failed data quality check'
        FROM trips WHERE {invalid_condition}
        """
    )

    deleted = execute_write(f"DELETE FROM trips WHERE {invalid_condition}")

    return {
        "dry_run":       False,
        "deleted_trips": deleted,
        "message":       f"{deleted} invalid trips removed and logged in audit_log.",
        "criteria": [
            "trip_distance_km IS NULL or <= 0",
            "fare_amount IS NULL or <= 0",
            "dropoff_datetime <= pickup_datetime",
            "pickup_zone_id IS NULL",
            "dropoff_zone_id IS NULL",
        ],
    }
