"""
tests_integration/test_revenue.py — Integration Tests · Revenue Service
Corre em: push para main, após docker-compose-test.yml estar up e seed.py executado.
Usa `requests` contra o serviço real — sem mocks.
"""

import pytest
import requests

BASE_URL = "http://localhost:8003"  # ajusta à porta do revenue-service no docker-compose-test.yml


def get(path, **params):
    return requests.get(f"{BASE_URL}{path}", params=params, timeout=10)


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

class TestRevenueServiceHealth:

    def test_avg_fare_reachable(self):
        assert get("/revenue/avg-fare-by-zone").status_code == 200

    def test_breakdown_reachable(self):
        assert get("/revenue/breakdown").status_code == 200

    def test_fare_per_km_reachable(self):
        assert get("/revenue/fare-per-km").status_code == 200

    def test_health_endpoint(self):
        r = get("/health")
        assert r.status_code == 200
        assert r.json()["service"] == "revenue"


# ---------------------------------------------------------------------------
# /revenue/avg-fare-by-zone
# ---------------------------------------------------------------------------

class TestAvgFareIntegration:

    def test_zones_not_empty_with_seeded_data(self):
        data = get("/revenue/avg-fare-by-zone").json()
        assert len(data["zones"]) > 0

    def test_global_avg_fare_positive(self):
        data = get("/revenue/avg-fare-by-zone").json()
        assert data["global_avg_fare"] > 0

    def test_avg_fare_positive_per_zone(self):
        for zone in get("/revenue/avg-fare-by-zone").json()["zones"]:
            assert zone["avg_fare"] > 0

    def test_trip_count_positive(self):
        for zone in get("/revenue/avg-fare-by-zone").json()["zones"]:
            assert zone["trip_count"] > 0

    def test_default_limit_respected(self):
        data = get("/revenue/avg-fare-by-zone").json()
        assert len(data["zones"]) <= 20

    def test_custom_limit_respected(self):
        data = get("/revenue/avg-fare-by-zone", limit=5).json()
        assert len(data["zones"]) <= 5

    def test_sort_desc_order(self):
        zones = get("/revenue/avg-fare-by-zone", sort="desc").json()["zones"]
        fares = [z["avg_fare"] for z in zones]
        assert fares == sorted(fares, reverse=True)

    def test_sort_asc_order(self):
        zones = get("/revenue/avg-fare-by-zone", sort="asc").json()["zones"]
        fares = [z["avg_fare"] for z in zones]
        assert fares == sorted(fares)

    def test_dropoff_zone_type_returns_200(self):
        assert get("/revenue/avg-fare-by-zone", zone_type="dropoff").status_code == 200

    def test_date_filter_returns_200(self):
        r = get("/revenue/avg-fare-by-zone", start_date="2015-01-01", end_date="2015-03-31")
        assert r.status_code == 200

    def test_end_before_start_returns_400(self):
        r = get("/revenue/avg-fare-by-zone", start_date="2015-06-01", end_date="2015-01-01")
        assert r.status_code == 400

    def test_limit_above_263_returns_422(self):
        assert get("/revenue/avg-fare-by-zone", limit=264).status_code == 422

    def test_zone_name_populated_via_grpc(self):
        """Com serviços reais, zone_name deve vir preenchido do Location Service."""
        zones = get("/revenue/avg-fare-by-zone").json()["zones"]
        populated = [z for z in zones if z["zone_name"] is not None]
        assert len(populated) > 0, "Esperado pelo menos uma zona com nome via gRPC"


# ---------------------------------------------------------------------------
# /revenue/breakdown
# ---------------------------------------------------------------------------

class TestBreakdownIntegration:

    def test_returns_200_with_seeded_data(self):
        assert get("/revenue/breakdown").status_code == 200

    def test_trip_count_positive(self):
        assert get("/revenue/breakdown").json()["trip_count"] > 0

    def test_avg_total_positive(self):
        assert get("/revenue/breakdown").json()["avg_total_amount"] > 0

    def test_all_components_present(self):
        bd = get("/revenue/breakdown").json()["breakdown"]
        for key in ("fare_amount", "tip_amount", "tolls_amount",
                    "mta_tax", "improvement_surcharge", "extra"):
            assert key in bd

    def test_percentages_sum_near_100(self):
        bd = get("/revenue/breakdown").json()["breakdown"]
        total = sum(v["percentage"] for v in bd.values())
        assert abs(total - 100.0) < 2.0

    def test_fare_amount_is_largest_component(self):
        bd = get("/revenue/breakdown").json()["breakdown"]
        assert bd["fare_amount"]["percentage"] > bd["tip_amount"]["percentage"]

    def test_dropoff_zone_type_returns_200(self):
        assert get("/revenue/breakdown", zone_type="dropoff").status_code == 200

    def test_date_filter_returns_200(self):
        assert get("/revenue/breakdown", start_date="2015-01-01", end_date="2015-06-30").status_code == 200

    def test_invalid_date_range_returns_400(self):
        assert get("/revenue/breakdown", start_date="2015-06-01", end_date="2015-01-01").status_code == 400

    def test_zone_filter_returns_200(self):
        assert get("/revenue/breakdown", zone_id=161).status_code == 200

    def test_unknown_zone_returns_404(self):
        assert get("/revenue/breakdown", zone_id=99999).status_code == 404


# ---------------------------------------------------------------------------
# /revenue/fare-per-km
# ---------------------------------------------------------------------------

class TestFarePerKmIntegration:

    def test_results_not_empty_with_seeded_data(self):
        data = get("/revenue/fare-per-km").json()
        assert data["total"] > 0

    def test_fare_per_km_positive(self):
        for entry in get("/revenue/fare-per-km").json()["results"]:
            assert entry["fare_per_km"] > 0

    def test_total_matches_results_length(self):
        data = get("/revenue/fare-per-km").json()
        assert data["total"] == len(data["results"])

    def test_default_limit_respected(self):
        data = get("/revenue/fare-per-km").json()
        assert len(data["results"]) <= 20

    def test_custom_limit_respected(self):
        data = get("/revenue/fare-per-km", limit=5).json()
        assert len(data["results"]) <= 5

    def test_order_by_fare_per_km_desc(self):
        results = get("/revenue/fare-per-km", order_by="fare_per_km").json()["results"]
        values = [r["fare_per_km"] for r in results]
        assert values == sorted(values, reverse=True)

    def test_order_by_zone_id_asc(self):
        results = get("/revenue/fare-per-km", order_by="zone_id").json()["results"]
        ids = [r["zone_id"] for r in results]
        assert ids == sorted(ids)

    def test_dropoff_zone_type_returns_200(self):
        assert get("/revenue/fare-per-km", zone_type="dropoff").status_code == 200

    def test_year_filter_returns_200(self):
        assert get("/revenue/fare-per-km", year=2015).status_code == 200

    def test_month_filter_returns_200(self):
        assert get("/revenue/fare-per-km", month=1).status_code == 200

    def test_invalid_month_returns_422(self):
        assert get("/revenue/fare-per-km", month=13).status_code == 422

    def test_limit_above_200_returns_422(self):
        assert get("/revenue/fare-per-km", limit=201).status_code == 422