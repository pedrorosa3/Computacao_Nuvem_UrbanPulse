"""
tests_integration/test_demand.py — Integration Tests · Demand Service
Corre em: push para main, após docker-compose-test.yml estar up e seed.py executado.
Usa `requests` contra o serviço real — sem mocks.
"""

import pytest
import requests

BASE_URL = "http://localhost:8002"


def get(path, **params):
    return requests.get(f"{BASE_URL}{path}", params=params, timeout=10)


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

class TestDemandServiceHealth:

    def test_hourly_matrix_reachable(self):
        r = get("/demand/hourly-matrix")
        assert r.status_code == 200, f"Serviço não responde: {r.text}"

    def test_monthly_trend_reachable(self):
        r = get("/demand/monthly-trend")
        assert r.status_code == 200, f"Serviço não responde: {r.text}"

    def test_hourly_matrix_returns_json(self):
        r = get("/demand/hourly-matrix")
        assert r.headers["content-type"].startswith("application/json")

    def test_monthly_trend_returns_json(self):
        r = get("/demand/monthly-trend")
        assert r.headers["content-type"].startswith("application/json")


# ---------------------------------------------------------------------------
# /hourly-matrix — dados (seed.py)
# ---------------------------------------------------------------------------

class TestHourlyMatrixIntegration:

    def test_matrix_has_7_days(self):
        data = get("/demand/hourly-matrix").json()
        assert len(data["matrix"]) == 7

    def test_each_day_has_24_hours(self):
        data = get("/demand/hourly-matrix").json()
        for day in data["matrix"]:
            assert len(day["hours"]) == 24

    def test_trip_counts_are_non_negative(self):
        data = get("/demand/hourly-matrix").json()
        for day in data["matrix"]:
            for h in day["hours"]:
                assert h["trip_count"] >= 0

    def test_overall_avg_positive_with_seeded_data(self):
        data = get("/demand/hourly-matrix").json()
        assert data["overall_avg_trips"] > 0, "Seed sem dados — overall_avg deve ser > 0"

    def test_at_least_one_peak_cell_with_seeded_data(self):
        data = get("/demand/hourly-matrix").json()
        peaks = [
            h for day in data["matrix"] for h in day["hours"] if h["is_peak"]
        ]
        assert len(peaks) > 0, "Esperado pelo menos um slot peak com dados reais"

    def test_filter_by_zone_returns_200(self):
        assert get("/demand/hourly-matrix", zone_id=161).status_code == 200

    def test_filter_by_year_returns_200(self):
        assert get("/demand/hourly-matrix", year=2015).status_code == 200

    def test_filter_by_month_returns_200(self):
        assert get("/demand/hourly-matrix", month=1).status_code == 200

    def test_filter_all_params_combined(self):
        r = get("/demand/hourly-matrix", zone_id=161, year=2015, month=1)
        assert r.status_code == 200
        f = r.json()["filters_applied"]
        assert f["zone_id"] == 161 and f["year"] == 2015 and f["month"] == 1

    def test_invalid_month_returns_422(self):
        assert get("/demand/hourly-matrix", month=13).status_code == 422

    def test_zone_with_no_data_returns_zeros(self):
        # zona inexistente → todos os counts devem ser 0
        data = get("/demand/hourly-matrix", zone_id=99999).json()
        for day in data["matrix"]:
            assert all(h["trip_count"] == 0 for h in day["hours"])


# ---------------------------------------------------------------------------
# /monthly-trend — dados (seed.py)
# ---------------------------------------------------------------------------

class TestMonthlyTrendIntegration:

    def test_months_list_not_empty_with_seeded_data(self):
        data = get("/demand/monthly-trend").json()
        assert len(data["months"]) > 0, "Seed sem dados — months deve ter entradas"

    def test_trend_direction_valid(self):
        td = get("/demand/monthly-trend").json()["trend_direction"]
        assert td in ("upward", "downward", "stable")

    def test_trip_counts_positive_with_seeded_data(self):
        for entry in get("/demand/monthly-trend").json()["months"]:
            assert entry["trip_count"] > 0

    def test_month_names_are_valid(self):
        import calendar
        valid = set(calendar.month_name[1:])
        for entry in get("/demand/monthly-trend").json()["months"]:
            assert entry["month_name"] in valid

    def test_months_ordered_chronologically(self):
        months = get("/demand/monthly-trend").json()["months"]
        pairs = [(m["year"], m["month"]) for m in months]
        assert pairs == sorted(pairs)

    def test_first_month_no_variation(self):
        months = get("/demand/monthly-trend").json()["months"]
        assert months[0]["variation_percentage"] is None

    def test_subsequent_months_have_variation(self):
        months = get("/demand/monthly-trend").json()["months"]
        if len(months) > 1:
            assert months[1]["variation_percentage"] is not None

    def test_filter_by_zone_returns_200(self):
        assert get("/demand/monthly-trend", zone_id=161).status_code == 200

    def test_filter_year_range(self):
        r = get("/demand/monthly-trend", year_from=2015, year_to=2015)
        assert r.status_code == 200
        for entry in r.json()["months"]:
            assert entry["year"] == 2015

    def test_compare_by_year(self):
        r = get("/demand/monthly-trend", compare_by="year")
        assert r.status_code == 200
        assert r.json()["filters_applied"]["compare_by"] == "year"

    def test_zone_with_no_data_returns_empty_months(self):
        data = get("/demand/monthly-trend", zone_id=99999).json()
        assert data["months"] == []
        assert data["trend_direction"] == "stable"