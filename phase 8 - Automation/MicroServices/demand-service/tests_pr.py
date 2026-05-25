"""
tests_pr.py — Pull Request Tests · Demand Service
Corre em: pull_request para main (job: pr-test)
Objetivo: validações extra de contrato e edge cases antes do merge.
Sem infraestrutura real — continua a usar mocks.
"""

import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers 
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
        monkeypatch.setattr("app.routers.hourly_matrix.get_conn", lambda: fake_get_conn(conn))
        return cur
    return _factory


@pytest.fixture()
def monthly_conn(monkeypatch):
    def _factory(rows):
        cur = make_cursor(rows)
        conn = make_conn(cur)
        monkeypatch.setattr("app.routers.monthly_trend.get_conn", lambda: fake_get_conn(conn))
        return cur
    return _factory


def hourly_rows(*tuples):
    return [{"day_of_week": d, "hour": h, "trip_count": c} for d, h, c in tuples]


def monthly_rows(*tuples):
    return [{"year": y, "month": m, "trip_count": c} for y, m, c in tuples]


# ---------------------------------------------------------------------------
# API — /hourly-matrix
# ---------------------------------------------------------------------------

class TestHourlyMatrixContract:

    def test_day_of_week_values_0_to_6(self, hourly_conn):
        hourly_conn([])
        matrix = client.get("/hourly-matrix").json()["matrix"]
        assert [d["day_of_week"] for d in matrix] == list(range(7))

    def test_trip_count_is_integer(self, hourly_conn):
        hourly_conn(hourly_rows((0, 0, 42)))
        h = client.get("/hourly-matrix").json()["matrix"][0]["hours"][0]
        assert isinstance(h["trip_count"], int)

    def test_is_peak_is_boolean(self, hourly_conn):
        hourly_conn([])
        h = client.get("/hourly-matrix").json()["matrix"][0]["hours"][0]
        assert isinstance(h["is_peak"], bool)

    def test_overall_avg_is_float_or_int(self, hourly_conn):
        hourly_conn([])
        avg = client.get("/hourly-matrix").json()["overall_avg_trips"]
        assert isinstance(avg, (int, float))

    def test_all_3_filter_params_combined(self, hourly_conn):
        hourly_conn([])
        r = client.get("/hourly-matrix?zone_id=10&year=2016&month=3")
        assert r.status_code == 200
        f = r.json()["filters_applied"]
        assert f == {"zone_id": 10, "year": 2016, "month": 3}

    def test_peak_factor_boundary(self, hourly_conn):
        """
        PEAK_FACTOR = 1.25. Com 168 células todas com 10 trips:
        overall_avg = 10, threshold = 12.5
        → célula com 12 não é peak, célula com 13 é peak.
        """
        base = [(d, h, 10) for d in range(7) for h in range(24)]
        # Substituir segunda hora 0 por 12 (abaixo do threshold)
        base[0] = (0, 0, 12)
        # Substituir terça hora 0 por 13 (acima do threshold)
        base[24] = (1, 0, 13)
        hourly_conn(hourly_rows(*base))
        matrix = client.get("/hourly-matrix").json()["matrix"]
        assert matrix[0]["hours"][0]["is_peak"] is False  # 12 < 12.5
        assert matrix[1]["hours"][0]["is_peak"] is True   # 13 >= 12.5


# ---------------------------------------------------------------------------
#  API — /monthly-trend
# ---------------------------------------------------------------------------

class TestMonthlyTrendContract:

    def test_trip_count_is_integer(self, monthly_conn):
        monthly_conn(monthly_rows((2015, 1, 500)))
        entry = client.get("/monthly-trend").json()["months"][0]
        assert isinstance(entry["trip_count"], int)

    def test_variation_percentage_is_float_or_none(self, monthly_conn):
        monthly_conn(monthly_rows((2015, 1, 1000), (2015, 2, 1500)))
        months = client.get("/monthly-trend").json()["months"]
        assert months[0]["variation_percentage"] is None
        assert isinstance(months[1]["variation_percentage"], float)

    def test_trend_direction_valid_values(self, monthly_conn):
        monthly_conn([])
        td = client.get("/monthly-trend").json()["trend_direction"]
        assert td in ("upward", "downward", "stable")

    def test_compare_by_default_month_in_filters(self, monthly_conn):
        monthly_conn([])
        assert client.get("/monthly-trend").json()["filters_applied"]["compare_by"] == "month"

    def test_compare_by_year_in_filters(self, monthly_conn):
        monthly_conn([])
        assert client.get("/monthly-trend?compare_by=year").json()["filters_applied"]["compare_by"] == "year"

    def test_year_from_and_year_to_reflected(self, monthly_conn):
        monthly_conn([])
        f = client.get("/monthly-trend?year_from=2015&year_to=2016").json()["filters_applied"]
        assert f["year_from"] == 2015 and f["year_to"] == 2016

    def test_variation_rounded_2_decimals(self, monthly_conn):
        monthly_conn(monthly_rows((2015, 1, 1000), (2015, 2, 1333)))
        var = client.get("/monthly-trend").json()["months"][1]["variation_percentage"]
        expected = round((1333 - 1000) / 1000 * 100, 2)
        assert var == expected

    def test_months_ordered_chronologically(self, monthly_conn):
        monthly_conn(monthly_rows(
            (2015, 1, 100), (2015, 6, 200), (2015, 12, 300), (2016, 3, 400)
        ))
        months = client.get("/monthly-trend").json()["months"]
        pairs = [(m["year"], m["month"]) for m in months]
        assert pairs == sorted(pairs)

    def test_trend_upward_2pct_boundary(self, monthly_conn):
        """
        diff_pct > 2 → upward. Testamos exactamente na fronteira:
        avg_start=100, avg_end=103 → diff=3% → upward.
        """
        monthly_conn(monthly_rows(
            (2015, 1, 100), (2015, 2, 100), (2015, 3, 100),
            (2015, 4, 103), (2015, 5, 103), (2015, 6, 103),
        ))
        assert client.get("/monthly-trend").json()["trend_direction"] == "upward"

    def test_trend_stable_within_2pct(self, monthly_conn):
        """
        diff_pct dentro de [-2, 2] → stable.
        avg_start=100, avg_end=101 → diff=1% → stable.
        """
        monthly_conn(monthly_rows(
            (2015, 1, 100), (2015, 2, 100), (2015, 3, 100),
            (2015, 4, 101), (2015, 5, 101), (2015, 6, 101),
        ))
        assert client.get("/monthly-trend").json()["trend_direction"] == "stable"