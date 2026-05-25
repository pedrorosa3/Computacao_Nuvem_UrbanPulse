"""
tests_pr.py — Pull Request Tests · Revenue Service
Corre em: pull_request para main (job: pr-test)
Objetivo: contrato de API, edge cases e boundary conditions antes do merge.
"""

import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers (standalone — não depende de conftest)
# ---------------------------------------------------------------------------

def make_cursor(rows=None, one=None):
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchall.return_value = rows or []
    cur.fetchone.return_value = one
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
    monkeypatch.setattr("app.routers.avg_fare.redis_client", None)
    monkeypatch.setattr("app.routers.breakdown.redis_client", None)
    monkeypatch.setattr("app.routers.fare_per_km.redis_client", None)


@pytest.fixture()
def avg_fare_conn(monkeypatch):
    def _f(rows):
        cur = make_cursor(rows=rows)
        monkeypatch.setattr("app.routers.avg_fare.get_conn", lambda: fake_get_conn(make_conn(cur)))
        return cur
    return _f


@pytest.fixture()
def breakdown_conn(monkeypatch):
    def _f(row):
        cur = make_cursor(one=row)
        monkeypatch.setattr("app.routers.breakdown.get_conn", lambda: fake_get_conn(make_conn(cur)))
        return cur
    return _f


@pytest.fixture()
def fare_per_km_conn(monkeypatch):
    def _f(rows):
        cur = make_cursor(rows=rows)
        monkeypatch.setattr("app.routers.fare_per_km.get_conn", lambda: fake_get_conn(make_conn(cur)))
        return cur
    return _f


@pytest.fixture()
def grpc_location(monkeypatch):
    zone = MagicMock()
    zone.zone_id = 161
    zone.zone_name = "Midtown Center"
    zone.borough = "Manhattan"
    stub = MagicMock()
    stub.GetZoneNames.return_value = MagicMock(zones=[zone])
    stub.GetZoneName.return_value = MagicMock(zone_name="Midtown Center", borough="Manhattan")
    monkeypatch.setattr("app.routers.avg_fare._get_location_stub", lambda: stub)
    monkeypatch.setattr("app.routers.breakdown._get_location_stub", lambda: stub)
    monkeypatch.setattr("app.routers.fare_per_km._get_location_stub", lambda: stub)
    return stub


@pytest.fixture()
def grpc_trip(monkeypatch):
    z = MagicMock()
    z.zone_id = 161
    z.avg_distance = 5.0
    stub = MagicMock()
    stub.GetDistanceByZone.return_value = MagicMock(zones=[z])
    monkeypatch.setattr("app.routers.fare_per_km._get_trip_stub", lambda: stub)
    return stub


def avg_row(zone_id=161, avg_fare=12.5, dev_abs=2.0, dev_pct=19.05,
            trip_count=1000, global_avg=10.5):
    return {"zone_id": zone_id, "avg_fare": avg_fare, "deviation_absolute": dev_abs,
            "deviation_percentage": dev_pct, "trip_count": trip_count, "global_avg_fare": global_avg}


def bd_row(trip_count=5000, avg_total=15.0, avg_fare=10.0, avg_tip=2.0,
           avg_tolls=0.5, avg_mta=0.5, avg_surcharge=0.3, avg_extra=0.2):
    return {"trip_count": trip_count, "avg_total": avg_total, "avg_fare": avg_fare,
            "avg_tip": avg_tip, "avg_tolls": avg_tolls, "avg_mta": avg_mta,
            "avg_surcharge": avg_surcharge, "avg_extra": avg_extra}


def fk_row(zone_id=161, avg_fare=12.0, trip_count=500):
    return {"zone_id": zone_id, "avg_fare": avg_fare, "trip_count": trip_count}


# ---------------------------------------------------------------------------
# Contrato — /revenue/avg-fare-by-zone
# ---------------------------------------------------------------------------

class TestAvgFareContract:

    def test_avg_fare_is_float(self, avg_fare_conn, grpc_location):
        avg_fare_conn([avg_row()])
        zone = client.get("/revenue/avg-fare-by-zone").json()["zones"][0]
        assert isinstance(zone["avg_fare"], float)

    def test_deviation_absolute_is_float(self, avg_fare_conn, grpc_location):
        avg_fare_conn([avg_row()])
        zone = client.get("/revenue/avg-fare-by-zone").json()["zones"][0]
        assert isinstance(zone["deviation_absolute"], float)

    def test_global_avg_fare_is_float(self, avg_fare_conn, grpc_location):
        avg_fare_conn([avg_row()])
        data = client.get("/revenue/avg-fare-by-zone").json()
        assert isinstance(data["global_avg_fare"], float)

    def test_trip_count_is_int(self, avg_fare_conn, grpc_location):
        avg_fare_conn([avg_row()])
        zone = client.get("/revenue/avg-fare-by-zone").json()["zones"][0]
        assert isinstance(zone["trip_count"], int)

    def test_default_limit_is_20(self, avg_fare_conn, grpc_location):
        avg_fare_conn([avg_row()])
        f = client.get("/revenue/avg-fare-by-zone").json()["filters_applied"]
        assert f["limit"] == 20

    def test_default_sort_is_desc(self, avg_fare_conn, grpc_location):
        avg_fare_conn([avg_row()])
        f = client.get("/revenue/avg-fare-by-zone").json()["filters_applied"]
        assert f["sort"] == "desc"

    def test_default_zone_type_is_pickup(self, avg_fare_conn, grpc_location):
        avg_fare_conn([avg_row()])
        f = client.get("/revenue/avg-fare-by-zone").json()["filters_applied"]
        assert f["zone_type"] == "pickup"

    def test_multiple_zones_returned(self, avg_fare_conn, grpc_location):
        rows = [avg_row(zone_id=i, avg_fare=float(10 + i)) for i in range(1, 6)]
        avg_fare_conn(rows)
        zones = client.get("/revenue/avg-fare-by-zone").json()["zones"]
        assert len(zones) == 5

    def test_start_date_equals_end_date_returns_200(self, avg_fare_conn, grpc_location):
        avg_fare_conn([])
        r = client.get("/revenue/avg-fare-by-zone?start_date=2015-06-01&end_date=2015-06-01")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Contrato — /revenue/breakdown
# ---------------------------------------------------------------------------

class TestBreakdownContract:

    def test_trip_count_is_int(self, breakdown_conn, grpc_location):
        breakdown_conn(bd_row())
        data = client.get("/revenue/breakdown").json()
        assert isinstance(data["trip_count"], int)

    def test_avg_total_is_float(self, breakdown_conn, grpc_location):
        breakdown_conn(bd_row())
        data = client.get("/revenue/breakdown").json()
        assert isinstance(data["avg_total_amount"], float)

    def test_each_component_has_avg_and_pct(self, breakdown_conn, grpc_location):
        breakdown_conn(bd_row())
        bd = client.get("/revenue/breakdown").json()["breakdown"]
        for comp in bd.values():
            assert isinstance(comp["avg"], float)
            assert isinstance(comp["percentage"], float)

    def test_percentages_non_negative(self, breakdown_conn, grpc_location):
        breakdown_conn(bd_row())
        bd = client.get("/revenue/breakdown").json()["breakdown"]
        for comp in bd.values():
            assert comp["percentage"] >= 0.0

    def test_fare_dominates_breakdown(self, breakdown_conn, grpc_location):
        """A tarifa base deve ser a maior componente."""
        breakdown_conn(bd_row(avg_total=15.0, avg_fare=10.0, avg_tip=2.0,
                               avg_tolls=0.5, avg_mta=0.5, avg_surcharge=0.3, avg_extra=0.2))
        bd = client.get("/revenue/breakdown").json()["breakdown"]
        assert bd["fare_amount"]["percentage"] > bd["tip_amount"]["percentage"]

    def test_dropoff_zone_type_reflected(self, breakdown_conn, grpc_location):
        breakdown_conn(bd_row())
        f = client.get("/revenue/breakdown?zone_type=dropoff").json()["filters_applied"]
        assert f["zone_type"] == "dropoff"

    def test_date_filters_reflected(self, breakdown_conn, grpc_location):
        breakdown_conn(bd_row())
        f = client.get("/revenue/breakdown?start_date=2015-01-01&end_date=2015-06-30").json()["filters_applied"]
        assert f["start_date"] == "2015-01-01"
        assert f["end_date"] == "2015-06-30"


# ---------------------------------------------------------------------------
# Contrato — /revenue/fare-per-km
# ---------------------------------------------------------------------------

class TestFarePerKmContract:

    def test_fare_per_km_is_float(self, fare_per_km_conn, grpc_trip, grpc_location):
        fare_per_km_conn([fk_row()])
        entry = client.get("/revenue/fare-per-km").json()["results"][0]
        assert isinstance(entry["fare_per_km"], float)

    def test_total_matches_results_length(self, fare_per_km_conn, grpc_trip, grpc_location):
        fare_per_km_conn([fk_row(zone_id=i) for i in range(1, 4)])
        # grpc_trip devolve apenas zona 161 → só 1 resultado (as outras ficam sem distância)
        data = client.get("/revenue/fare-per-km").json()
        assert data["total"] == len(data["results"])

    def test_default_order_by_fare_per_km(self, fare_per_km_conn, grpc_trip, grpc_location):
        fare_per_km_conn([fk_row()])
        f = client.get("/revenue/fare-per-km").json()["filters"]
        assert f["order_by"] == "fare_per_km"

    def test_default_zone_type_is_pickup(self, fare_per_km_conn, grpc_trip, grpc_location):
        fare_per_km_conn([])
        f = client.get("/revenue/fare-per-km").json()["filters"]
        assert f["zone_type"] == "pickup"

    def test_limit_above_200_returns_422(self, fare_per_km_conn, grpc_trip, grpc_location):
        fare_per_km_conn([])
        assert client.get("/revenue/fare-per-km?limit=201").status_code == 422

    def test_zone_type_dropoff_reflected(self, fare_per_km_conn, grpc_trip, grpc_location):
        fare_per_km_conn([])
        f = client.get("/revenue/fare-per-km?zone_type=dropoff").json()["filters"]
        assert f["zone_type"] == "dropoff"

    def test_year_and_month_reflected(self, fare_per_km_conn, grpc_trip, grpc_location):
        fare_per_km_conn([])
        f = client.get("/revenue/fare-per-km?year=2015&month=6").json()["filters"]
        assert f["year"] == 2015 and f["month"] == 6

    def test_location_grpc_failure_graceful(self, fare_per_km_conn, grpc_trip, monkeypatch):
        """Falha do Location Service não deve quebrar o endpoint — zona_name fica None."""
        fare_per_km_conn([fk_row()])
        import grpc
        stub = MagicMock()
        stub.GetZoneNames.side_effect = grpc.RpcError()
        monkeypatch.setattr("app.routers.fare_per_km._get_location_stub", lambda: stub)
        data = client.get("/revenue/fare-per-km").json()
        assert data["results"][0]["zone_name"] is None