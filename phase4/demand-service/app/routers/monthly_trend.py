from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.db.connection import get_conn
import calendar

router = APIRouter()


@router.get("/monthly-trend", summary="UC16 – Monthly trip volume trend with percentage variation")
def monthly_trend(
    zone_id:    Optional[int] = Query(None, example=161),
    year_from:  Optional[int] = Query(None, example=2015),
    year_to:    Optional[int] = Query(None, example=2016),
    compare_by: str           = Query("month", enum=["month", "year"]),
):
    conditions = ["pickup_datetime IS NOT NULL"]
    params: list = []
    if zone_id is not None:
        conditions.append("pickup_zone_id = %s")
        params.append(zone_id)
    if year_from:
        conditions.append("EXTRACT(YEAR FROM pickup_datetime) >= %s")
        params.append(year_from)
    if year_to:
        conditions.append("EXTRACT(YEAR FROM pickup_datetime) <= %s")
        params.append(year_to)
    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            EXTRACT(YEAR  FROM pickup_datetime)::INT AS year,
            EXTRACT(MONTH FROM pickup_datetime)::INT AS month,
            COUNT(*) AS trip_count
        FROM trips
        {where}
        GROUP BY year, month
        ORDER BY year, month
    """

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not rows:
        return {
            "filters_applied": {
                "zone_id": zone_id, "year_from": year_from,
                "year_to": year_to, "compare_by": compare_by,
            },
            "trend_direction": "stable",
            "months": [],
        }

    # Build lookup for variation calculation
    count_map: dict[tuple, int] = {
        (r["year"], r["month"]): int(r["trip_count"]) for r in rows
    }

    months_out = []
    for r in rows:
        yr, mo, cnt = int(r["year"]), int(r["month"]), int(r["trip_count"])

        # Determine reference period
        if compare_by == "month":
            # Previous calendar month
            ref_yr  = yr if mo > 1 else yr - 1
            ref_mo  = mo - 1 if mo > 1 else 12
        else:
            # Same month, previous year
            ref_yr, ref_mo = yr - 1, mo

        ref_count = count_map.get((ref_yr, ref_mo))
        if ref_count and ref_count > 0:
            variation = round((cnt - ref_count) / ref_count * 100, 2)
        else:
            variation = None

        months_out.append({
            "year":                 yr,
            "month":                mo,
            "month_name":           calendar.month_name[mo],
            "trip_count":           cnt,
            "variation_percentage": variation,
        })

    # Overall trend: compare average of last third vs first third of the period
    counts = [m["trip_count"] for m in months_out]
    n = len(counts)
    if n >= 3:
        third = max(n // 3, 1)
        avg_start = sum(counts[:third]) / third
        avg_end   = sum(counts[-third:]) / third
        diff_pct  = (avg_end - avg_start) / avg_start * 100 if avg_start else 0
        if diff_pct > 2:
            trend = "upward"
        elif diff_pct < -2:
            trend = "downward"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return {
        "filters_applied": {
            "zone_id":    zone_id,
            "year_from":  year_from,
            "year_to":    year_to,
            "compare_by": compare_by,
        },
        "trend_direction": trend,
        "months":          months_out,
    }
