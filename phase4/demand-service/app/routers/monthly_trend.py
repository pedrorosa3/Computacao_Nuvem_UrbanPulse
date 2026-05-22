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
    # Usar colunas pré-calculadas em vez de EXTRACT()
    conditions = []
    params: list = []
    if zone_id is not None:
        conditions.append("pickup_zone_id = %s")
        params.append(zone_id)
    if year_from:
        conditions.append("pickup_year >= %s")
        params.append(year_from)
    if year_to:
        conditions.append("pickup_year <= %s")
        params.append(year_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    query = f"""
        SELECT
            pickup_year  AS year,
            pickup_month AS month,
            COUNT(*)     AS trip_count
        FROM trips
        {where}
        GROUP BY pickup_year, pickup_month
        ORDER BY pickup_year, pickup_month
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

    count_map: dict[tuple, int] = {
        (r["year"], r["month"]): int(r["trip_count"]) for r in rows
    }

    months_out = []
    for r in rows:
        yr, mo, cnt = int(r["year"]), int(r["month"]), int(r["trip_count"])

        if compare_by == "month":
            ref_yr = yr if mo > 1 else yr - 1
            ref_mo = mo - 1 if mo > 1 else 12
        else:
            ref_yr, ref_mo = yr - 1, mo

        ref_count = count_map.get((ref_yr, ref_mo))
        variation = round((cnt - ref_count) / ref_count * 100, 2) if ref_count else None

        months_out.append({
            "year":                 yr,
            "month":                mo,
            "month_name":           calendar.month_name[mo],
            "trip_count":           cnt,
            "variation_percentage": variation,
        })

    counts = [m["trip_count"] for m in months_out]
    n = len(counts)
    if n >= 3:
        third = max(n // 3, 1)
        avg_start = sum(counts[:third]) / third
        avg_end   = sum(counts[-third:]) / third
        diff_pct  = (avg_end - avg_start) / avg_start * 100 if avg_start else 0
        trend = "upward" if diff_pct > 2 else "downward" if diff_pct < -2 else "stable"
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