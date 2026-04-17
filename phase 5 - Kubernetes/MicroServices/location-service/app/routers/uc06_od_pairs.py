from fastapi import APIRouter, Query, HTTPException
from datetime import date
from app.database import execute_query

router = APIRouter()

@router.get("/locations/pairs")
def get_od_pairs(
    start_date: date = Query(None),
    end_date:   date = Query(None),
    limit:      int  = Query(20, ge=1, le=100),
    min_trips:  int  = Query(100, ge=1),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    # Filtros de data
    filters = []
    params  = []
    if start_date:
        filters.append("t.pickup_date >= %s")
        params.append(start_date)
    if end_date:
        filters.append("t.pickup_date <= %s")
        params.append(end_date)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    query = f"""
        WITH pair_counts AS (
            SELECT
                pickup_zone_id,
                dropoff_zone_id,
                COUNT(*) AS trip_count
            FROM trips t
            {where}
            GROUP BY pickup_zone_id, dropoff_zone_id
        ),
        origin_totals AS (
            SELECT pickup_zone_id, SUM(trip_count) AS total_from
            FROM pair_counts
            GROUP BY pickup_zone_id
        ),
        dest_totals AS (
            SELECT dropoff_zone_id, SUM(trip_count) AS total_to
            FROM pair_counts
            GROUP BY dropoff_zone_id
        ),
        city_total AS (
            SELECT SUM(trip_count) AS total FROM pair_counts
        ),
        affinity AS (
            SELECT
                pc.pickup_zone_id,
                pc.dropoff_zone_id,
                pc.trip_count,
                ot.total_from,
                dt.total_to,
                ROUND(
                    (pc.trip_count::numeric / (ot.total_from * dt.total_to) * ot.total_from * dt.total_to / NULLIF(ot.total_from * dt.total_to / ct.total::numeric, 0))::numeric,
                    4
                ) AS affinity_index,
                ROUND((pc.trip_count * 100.0 / ct.total)::numeric, 2) AS relative_frequency_pct
            FROM pair_counts pc
            JOIN origin_totals ot ON ot.pickup_zone_id  = pc.pickup_zone_id
            JOIN dest_totals   dt ON dt.dropoff_zone_id = pc.dropoff_zone_id
            CROSS JOIN city_total ct
            WHERE pc.trip_count >= %s
        )
        SELECT
            ROW_NUMBER() OVER (ORDER BY affinity_index DESC) AS rank,
            a.pickup_zone_id                                  AS origin_zone_id,
            zo.zone_name                                      AS origin_zone_name,
            zo.borough                                        AS origin_borough,
            a.dropoff_zone_id                                 AS destination_zone_id,
            zd.zone_name                                      AS destination_zone_name,
            zd.borough                                        AS destination_borough,
            a.trip_count,
            a.affinity_index,
            a.relative_frequency_pct
        FROM affinity a
        JOIN zones zo ON zo.location_id = a.pickup_zone_id
        JOIN zones zd ON zd.location_id = a.dropoff_zone_id
        ORDER BY affinity_index DESC
        LIMIT %s
    """

    # Total de viagens no período
    total_rows = execute_query(
        f"SELECT COUNT(*) AS total FROM trips t {where}",
        tuple(params)
    )
    total_trips = total_rows[0]["total"]

    params_query = tuple(params) + (min_trips, limit)
    rows = execute_query(query, params_query)

    return {
        "period": {
            "start_date": str(start_date) if start_date else None,
            "end_date":   str(end_date)   if end_date   else None,
        },
        "total_trips": total_trips,
        "pairs": [
            {
                "rank":                  int(row["rank"]),
                "origin_zone_id":        row["origin_zone_id"],
                "origin_zone_name":      row["origin_zone_name"],
                "origin_borough":        row["origin_borough"],
                "destination_zone_id":   row["destination_zone_id"],
                "destination_zone_name": row["destination_zone_name"],
                "destination_borough":   row["destination_borough"],
                "trip_count":            row["trip_count"],
                "affinity_index":        float(row["affinity_index"]),
                "relative_frequency_pct": float(row["relative_frequency_pct"]),
            }
            for row in rows
        ],
    }
