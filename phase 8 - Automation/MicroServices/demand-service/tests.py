"""
tests.py — Unit Tests · Demand Service
Corre em: todo push e PR (job: unit-test)
Estratégia: mock total de DB e Redis, sem infraestrutura externa.
"""

import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def make_cursor(rows):
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchall.return_value = rows
    return cur


def make_conn(cursor):
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor
    return conn


@contextmanager
def fake_get_conn(conn):
    yield conn


@pytest.fixture(autouse=True)
def disable_redis(monkeypatch):
    monkeypatch.setattr("app.routers.hourly_matrix.redis_client", None)
    monkeypatch.setattr("app.routers.monthly_trend.redis_client", None)


@pytest.fixture()
def hourly_conn(monkeypatch):
    def _factory(rows):
        cur = make_cursor(rows)
        conn = make_conn(cur)
        monkeypatch.setattr(
            "app.routers.hourly_matrix.get_conn",
            lambda: fake_get_conn(conn),
        )
        return cur
    return _factory


@pytest.fixture()
def monthly_conn(monkeypatch):
    def _factory(rows):
        cur = make_cursor(rows)
        conn = make_conn(cur)
        monkeypatch.setattr(
            "app.routers.monthly_trend.get_conn",
            lambda: fake_get_conn(conn),
        )
        return cur
    return _factory


def hourly_rows(*tuples):
    """(day_of_week, hour, trip_count) → list of dicts"""
    return [{"day_of_week": d, "hour": h, "trip_count": c} for d, h, c in tuples]


def monthly_rows(*tuples):
    """(year, month, trip_count) → list of dicts"""
    return [{"year": y, "month": m, "trip_count": c} for y, m, c in tuples]


# ---------------------------------------------------------------------------
# /hourly-matrix — estrutura
# ---------------------------------------------------------------------------

class TestHourlyMatrixStructure:

    def test_returns_200(self, hourly_conn):
        hourly_conn([])
        assert client.get("/demand/hourly-matrix").status_code == 200

    def test_response_keys_present(self, hourly_conn):
        hourly_conn([])
        data = client.get("/demand/hourly-matrix").json()
        assert "matrix" in data
        assert "overall_avg_trips" in data
        assert "filters_applied" in data

    def test_matrix_has_7_days(self, hourly_conn):
        hourly_conn([])
        assert len(client.get("/demand/hourly-matrix").json()["matrix"]) == 7

    def test_each_day_has_24_hours(self, hourly_conn):
        hourly_conn([])
        for day in client.get("/demand/hourly-matrix").json()["matrix"]:
            assert len(day["hours"]) == 24

    def test_day_names_order(self, hourly_conn):
        hourly_conn([])
        names = [d["day_name"] for d in client.get("/demand/hourly-matrix").json()["matrix"]]
        assert names == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def test_hours_range_0_to_23(self, hourly_conn):
        hourly_conn([])
        for day in client.get("/demand/hourly-matrix").json()["matrix"]:
            assert [h["hour"] for h in day["hours"]] == list(range(24))

    def test_hour_entry_has_required_keys(self, hourly_conn):
        hourly_conn([])
        h = client.get("/demand/hourly-matrix").json()["matrix"][0]["hours"][0]
        assert "hour" in h and "trip_count" in h and "is_peak" in h


# ---------------------------------------------------------------------------
# /hourly-matrix — lógica
# ---------------------------------------------------------------------------

class TestHourlyMatrixLogic:

    def test_empty_db_all_zeros(self, hourly_conn):
        hourly_conn([])
        for day in client.get("/demand/hourly-matrix").json()["matrix"]:
            assert all(h["trip_count"] == 0 for h in day["hours"])

    def test_empty_db_overall_avg_zero(self, hourly_conn):
        hourly_conn([])
        assert client.get("/demand/hourly-matrix").json()["overall_avg_trips"] == 0.0

    def test_trip_count_placed_correctly(self, hourly_conn):
        hourly_conn(hourly_rows((0, 9, 500), (3, 15, 200)))
        matrix = client.get("/demand/hourly-matrix").json()["matrix"]
        assert matrix[0]["hours"][9]["trip_count"] == 500
        assert matrix[3]["hours"][15]["trip_count"] == 200

    def test_missing_cell_defaults_to_zero(self, hourly_conn):
        hourly_conn(hourly_rows((0, 0, 100)))
        assert client.get("/demand/hourly-matrix").json()["matrix"][0]["hours"][1]["trip_count"] == 0

    def test_is_peak_true_for_high_cell(self, hourly_conn):
        # 1 célula com 1000, restantes 0 → só essa é peak
        hourly_conn(hourly_rows((0, 0, 1000)))
        assert client.get("/demand/hourly-matrix").json()["matrix"][0]["hours"][0]["is_peak"] is True

    def test_is_peak_false_for_zero_cells(self, hourly_conn):
        hourly_conn(hourly_rows((0, 0, 1000)))
        matrix = client.get("/demand/hourly-matrix").json()["matrix"]
        assert matrix[0]["hours"][1]["is_peak"] is False

    def test_is_peak_false_when_avg_zero(self, hourly_conn):
        hourly_conn([])
        for day in client.get("/demand/hourly-matrix").json()["matrix"]:
            assert all(h["is_peak"] is False for h in day["hours"])

    def test_overall_avg_uniform_data(self, hourly_conn):
        # 168 células, todas com 1 trip → avg = 1.0
        hourly_conn(hourly_rows(*[(d, h, 1) for d in range(7) for h in range(24)]))
        assert client.get("/demand/hourly-matrix").json()["overall_avg_trips"] == 1.0


# ---------------------------------------------------------------------------
# /hourly-matrix — filtros e validação
# ---------------------------------------------------------------------------

class TestHourlyMatrixFilters:

    def test_zone_id_reflected(self, hourly_conn):
        hourly_conn([])
        assert client.get("/demand/hourly-matrix?zone_id=161").json()["filters_applied"]["zone_id"] == 161

    def test_year_reflected(self, hourly_conn):
        hourly_conn([])
        assert client.get("/demand/hourly-matrix?year=2015").json()["filters_applied"]["year"] == 2015

    def test_month_reflected(self, hourly_conn):
        hourly_conn([])
        assert client.get("/demand/hourly-matrix?month=6").json()["filters_applied"]["month"] == 6

    def test_no_filters_all_none(self, hourly_conn):
        hourly_conn([])
        f = client.get("/demand/hourly-matrix").json()["filters_applied"]
        assert f == {"zone_id": None, "year": None, "month": None}

    def test_month_0_returns_422(self, hourly_conn):
        hourly_conn([])
        assert client.get("/demand/hourly-matrix?month=0").status_code == 422

    def test_month_13_returns_422(self, hourly_conn):
        hourly_conn([])
        assert client.get("/demand/hourly-matrix?month=13").status_code == 422

    def test_db_error_returns_500(self, monkeypatch, disable_redis):
        monkeypatch.setattr("app.routers.hourly_matrix.get_conn", lambda: (_ for _ in ()).throw(Exception("fail")))
        assert client.get("/demand/hourly-matrix").status_code == 500


# ---------------------------------------------------------------------------
# /monthly-trend — estrutura
# ---------------------------------------------------------------------------

class TestMonthlyTrendStructure:

    def test_returns_200(self, monthly_conn):
        monthly_conn([])
        assert client.get("/demand/monthly-trend").status_code == 200

    def test_response_keys_present(self, monthly_conn):
        monthly_conn([])
        data = client.get("/demand/monthly-trend").json()
        assert "filters_applied" in data and "trend_direction" in data and "months" in data

    def test_empty_db_months_empty(self, monthly_conn):
        monthly_conn([])
        assert client.get("/demand/monthly-trend").json()["months"] == []

    def test_month_entry_keys(self, monthly_conn):
        monthly_conn(monthly_rows((2015, 6, 1000)))
        entry = client.get("/demand/monthly-trend").json()["months"][0]
        for k in ("year", "month", "month_name", "trip_count", "variation_percentage"):
            assert k in entry

    def test_month_name_correct(self, monthly_conn):
        monthly_conn(monthly_rows((2015, 1, 100), (2015, 6, 200), (2015, 12, 300)))
        months = {m["month"]: m["month_name"] for m in client.get("/demand/monthly-trend").json()["months"]}
        assert months[1] == "January" and months[6] == "June" and months[12] == "December"


# ---------------------------------------------------------------------------
# /monthly-trend — variação percentual
# ---------------------------------------------------------------------------

class TestMonthlyTrendVariation:

    def test_first_month_no_variation(self, monthly_conn):
        monthly_conn(monthly_rows((2015, 1, 1000)))
        assert client.get("/demand/monthly-trend").json()["months"][0]["variation_percentage"] is None

    def test_variation_positive(self, monthly_conn):
        monthly_conn(monthly_rows((2015, 1, 1000), (2015, 2, 1500)))
        assert client.get("/demand/monthly-trend").json()["months"][1]["variation_percentage"] == 50.0

    def test_variation_negative(self, monthly_conn):
        monthly_conn(monthly_rows((2015, 1, 2000), (2015, 2, 1000)))
        assert client.get("/demand/monthly-trend").json()["months"][1]["variation_percentage"] == -50.0

    def test_variation_across_year_boundary(self, monthly_conn):
        monthly_conn(monthly_rows((2015, 12, 2000), (2016, 1, 1000)))
        months = client.get("/demand/monthly-trend").json()["months"]
        jan = next(m for m in months if m["year"] == 2016)
        assert jan["variation_percentage"] == -50.0

    def test_compare_by_year(self, monthly_conn):
        monthly_conn(monthly_rows((2015, 6, 1000), (2016, 6, 2000)))
        months = client.get("/demand/monthly-trend?compare_by=year").json()["months"]
        jun_2016 = next(m for m in months if m["year"] == 2016)
        assert jun_2016["variation_percentage"] == 100.0

    def test_invalid_compare_by_returns_422(self, monthly_conn):
        monthly_conn([])
        assert client.get("/demand/monthly-trend?compare_by=week").status_code == 422


# ---------------------------------------------------------------------------
# /monthly-trend — trend_direction
# ---------------------------------------------------------------------------

class TestMonthlyTrendDirection:

    def test_upward(self, monthly_conn):
        monthly_conn(monthly_rows(
            (2015, 1, 1000), (2015, 2, 1100), (2015, 3, 1200),
            (2015, 4, 1400), (2015, 5, 1800), (2015, 6, 2000),
        ))
        assert client.get("/demand/monthly-trend").json()["trend_direction"] == "upward"

    def test_downward(self, monthly_conn):
        monthly_conn(monthly_rows(
            (2015, 1, 2000), (2015, 2, 1800), (2015, 3, 1400),
            (2015, 4, 1200), (2015, 5, 1100), (2015, 6, 1000),
        ))
        assert client.get("/demand/monthly-trend").json()["trend_direction"] == "downward"

    def test_stable_flat(self, monthly_conn):
        monthly_conn(monthly_rows(*[(2015, m, 1000) for m in range(1, 7)]))
        assert client.get("/demand/monthly-trend").json()["trend_direction"] == "stable"

    def test_stable_less_than_3_points(self, monthly_conn):
        monthly_conn(monthly_rows((2015, 1, 100), (2015, 2, 9999)))
        assert client.get("/demand/monthly-trend").json()["trend_direction"] == "stable"

    def test_stable_empty(self, monthly_conn):
        monthly_conn([])
        assert client.get("/demand/monthly-trend").json()["trend_direction"] == "stable"

    def test_db_error_returns_500(self, monkeypatch, disable_redis):
        monkeypatch.setattr("app.routers.monthly_trend.get_conn", lambda: (_ for _ in ()).throw(Exception("fail")))
        assert client.get("/demand/monthly-trend").status_code == 500