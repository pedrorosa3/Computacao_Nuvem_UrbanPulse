"""
tests.py — Unit Tests · Revenue Service
Corre em: todo push e PR (job: unit-test)
Estratégia: mock total de DB, Redis e gRPC — sem infraestrutura externa.
"""

import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_cursor(rows=None, one=None):
    """rows → fetchall(); one → fetchone()"""
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def disable_redis(monkeypatch):
    monkeypatch.setattr("app.routers.avg_fare.redis_client", None)
    monkeypatch.setattr("app.routers.breakdown.redis_client", None)
    monkeypatch.setattr("app.routers.fare_per_km.redis_client", None)


@pytest.fixture()
def avg_fare_conn(monkeypatch):
    def _factory(rows):
        cur = make_cursor(rows=rows)
        conn = make_conn(cur)
        monkeypatch.setattr("app.routers.avg_fare.get_conn", lambda: fake_get_conn(conn))
        return cur
    return _factory


@pytest.fixture()
def breakdown_conn(monkeypatch):
    def _factory(row):
        cur = make_cursor(one=row)
        conn = make_conn(cur)
        monkeypatch.setattr("app.routers.breakdown.get_conn", lambda: fake_get_conn(conn))
        return cur
    return _factory


@pytest.fixture()
def fare_per_km_conn(monkeypatch):
    def _factory(rows):
        cur = make_cursor(rows=rows)
        conn = make_conn(cur)
        monkeypatch.setattr("app.routers.fare_per_km.get_conn", lambda: fake_get_conn(conn))
        return cur
    return _factory


@pytest.fixture()
def mock_grpc_location(monkeypatch):
    """Stub gRPC do Location Service — devolve zona mock."""
    def _factory(zones=None):
        zone = MagicMock()
        zone.zone_id = 161
        zone.zone_name = "Midtown Center"
        zone.borough = "Manhattan"

        stub = MagicMock()
        stub.GetZoneNames.return_value = MagicMock(zones=zones or [zone])
        stub.GetZoneName.return_value = MagicMock(zone_name="Midtown Center", borough="Manhattan")

        monkeypatch.setattr("app.routers.avg_fare._get_location_stub", lambda: stub)
        monkeypatch.setattr("app.routers.breakdown._get_location_stub", lambda: stub)
        monkeypatch.setattr("app.routers.fare_per_km._get_location_stub", lambda: stub)
        return stub
    return _factory


@pytest.fixture()
def mock_grpc_trip(monkeypatch):
    """Stub gRPC do Trip Service — devolve distância mock por zona."""
    def _factory(zones=None):
        z = MagicMock()
        z.zone_id = 161
        z.avg_distance = 5.0

        stub = MagicMock()
        stub.GetDistanceByZone.return_value = MagicMock(zones=zones or [z])

        monkeypatch.setattr("app.routers.fare_per_km._get_trip_stub", lambda: stub)
        return stub
    return _factory


# ---------------------------------------------------------------------------
# /revenue/avg-fare-by-zone
# ---------------------------------------------------------------------------

def avg_fare_row(zone_id=161, avg_fare=12.50, deviation_abs=2.0,
                 deviation_pct=19.05, trip_count=1000, global_avg=10.50):
    return {
        "zone_id": zone_id,
        "avg_fare": avg_fare,
        "deviation_absolute": deviation_abs,
        "deviation_percentage": deviation_pct,
        "trip_count": trip_count,
        "global_avg_fare": global_avg,
    }


class TestAvgFareStructure:

    def test_returns_200(self, avg_fare_conn, mock_grpc_location):
        avg_fare_conn([avg_fare_row()])
        mock_grpc_location()
        assert client.get("/revenue/avg-fare-by-zone").status_code == 200

    def test_response_keys(self, avg_fare_conn, mock_grpc_location):
        avg_fare_conn([avg_fare_row()])
        mock_grpc_location()
        data = client.get("/revenue/avg-fare-by-zone").json()
        assert "filters_applied" in data
        assert "global_avg_fare" in data
        assert "zones" in data

    def test_empty_db_returns_empty_zones(self, avg_fare_conn, mock_grpc_location):
        avg_fare_conn([])
        mock_grpc_location()
        data = client.get("/revenue/avg-fare-by-zone").json()
        assert data["zones"] == []
        assert data["global_avg_fare"] is None

    def test_zone_entry_has_required_keys(self, avg_fare_conn, mock_grpc_location):
        avg_fare_conn([avg_fare_row()])
        mock_grpc_location()
        zone = client.get("/revenue/avg-fare-by-zone").json()["zones"][0]
        for k in ("zone_id", "zone_name", "borough", "avg_fare",
                  "deviation_absolute", "deviation_percentage", "trip_count"):
            assert k in zone

    def test_zone_name_from_grpc(self, avg_fare_conn, mock_grpc_location):
        avg_fare_conn([avg_fare_row(zone_id=161)])
        mock_grpc_location()
        zone = client.get("/revenue/avg-fare-by-zone").json()["zones"][0]
        assert zone["zone_name"] == "Midtown Center"
        assert zone["borough"] == "Manhattan"

    def test_grpc_failure_returns_null_zone_info(self, avg_fare_conn, monkeypatch):
        avg_fare_conn([avg_fare_row()])
        import grpc
        stub = MagicMock()
        stub.GetZoneNames.side_effect = grpc.RpcError()
        monkeypatch.setattr("app.routers.avg_fare._get_location_stub", lambda: stub)
        zone = client.get("/revenue/avg-fare-by-zone").json()["zones"][0]
        assert zone["zone_name"] is None
        assert zone["borough"] is None


class TestAvgFareFilters:

    def test_filters_reflected(self, avg_fare_conn, mock_grpc_location):
        avg_fare_conn([])
        mock_grpc_location()
        f = client.get("/revenue/avg-fare-by-zone?zone_type=dropoff&sort=asc&limit=5").json()["filters_applied"]
        assert f["zone_type"] == "dropoff"
        assert f["sort"] == "asc"
        assert f["limit"] == 5

    def test_end_date_before_start_date_returns_400(self, avg_fare_conn, mock_grpc_location):
        avg_fare_conn([])
        mock_grpc_location()
        r = client.get("/revenue/avg-fare-by-zone?start_date=2015-06-01&end_date=2015-01-01")
        assert r.status_code == 400

    def test_limit_below_1_returns_422(self, avg_fare_conn, mock_grpc_location):
        avg_fare_conn([])
        mock_grpc_location()
        assert client.get("/revenue/avg-fare-by-zone?limit=0").status_code == 422

    def test_limit_above_263_returns_422(self, avg_fare_conn, mock_grpc_location):
        avg_fare_conn([])
        mock_grpc_location()
        assert client.get("/revenue/avg-fare-by-zone?limit=264").status_code == 422

    def test_db_error_returns_500(self, monkeypatch):
        monkeypatch.setattr("app.routers.avg_fare.get_conn", lambda: (_ for _ in ()).throw(Exception("fail")))
        assert client.get("/revenue/avg-fare-by-zone").status_code == 500


# ---------------------------------------------------------------------------
# /revenue/breakdown
# ---------------------------------------------------------------------------

def breakdown_row(trip_count=5000, avg_total=15.0, avg_fare=10.0, avg_tip=2.0,
                  avg_tolls=0.5, avg_mta=0.5, avg_surcharge=0.3, avg_extra=0.2):
    return {
        "trip_count": trip_count,
        "avg_total": avg_total,
        "avg_fare": avg_fare,
        "avg_tip": avg_tip,
        "avg_tolls": avg_tolls,
        "avg_mta": avg_mta,
        "avg_surcharge": avg_surcharge,
        "avg_extra": avg_extra,
    }


class TestBreakdownStructure:

    def test_returns_200(self, breakdown_conn, mock_grpc_location):
        breakdown_conn(breakdown_row())
        mock_grpc_location()
        assert client.get("/revenue/breakdown").status_code == 200

    def test_response_keys(self, breakdown_conn, mock_grpc_location):
        breakdown_conn(breakdown_row())
        mock_grpc_location()
        data = client.get("/revenue/breakdown").json()
        assert "filters_applied" in data
        assert "trip_count" in data
        assert "avg_total_amount" in data
        assert "breakdown" in data

    def test_breakdown_components_present(self, breakdown_conn, mock_grpc_location):
        breakdown_conn(breakdown_row())
        mock_grpc_location()
        bd = client.get("/revenue/breakdown").json()["breakdown"]
        for key in ("fare_amount", "tip_amount", "tolls_amount",
                    "mta_tax", "improvement_surcharge", "extra"):
            assert key in bd
            assert "avg" in bd[key]
            assert "percentage" in bd[key]

    def test_no_data_returns_404(self, breakdown_conn, mock_grpc_location):
        breakdown_conn({"trip_count": 0})
        mock_grpc_location()
        assert client.get("/revenue/breakdown").status_code == 404

    def test_null_row_returns_404(self, breakdown_conn, mock_grpc_location):
        breakdown_conn(None)
        mock_grpc_location()
        assert client.get("/revenue/breakdown").status_code == 404


class TestBreakdownLogic:

    def test_percentages_sum_to_100(self, breakdown_conn, mock_grpc_location):
        """A soma das percentagens deve ser ~100% (pode diferir por arredondamento)."""
        # componentes somam exactamente avg_total → percentagens devem somar 100%
        breakdown_conn(breakdown_row(
            avg_total=15.0, avg_fare=10.0, avg_tip=2.0,
            avg_tolls=1.0, avg_mta=1.0, avg_surcharge=0.5, avg_extra=0.5,
        ))
        mock_grpc_location()
        bd = client.get("/revenue/breakdown").json()["breakdown"]
        total_pct = sum(v["percentage"] for v in bd.values())
        assert abs(total_pct - 100.0) < 1.0  # tolerância de arredondamento

    def test_fare_percentage_correct(self, breakdown_conn, mock_grpc_location):
        """fare=10, total=20 → 50%"""
        breakdown_conn(breakdown_row(avg_total=20.0, avg_fare=10.0, avg_tip=4.0,
                                     avg_tolls=2.0, avg_mta=2.0, avg_surcharge=1.0, avg_extra=1.0))
        mock_grpc_location()
        bd = client.get("/revenue/breakdown").json()["breakdown"]
        assert bd["fare_amount"]["percentage"] == 50.0

    def test_zone_info_present_when_zone_id_given(self, breakdown_conn, mock_grpc_location):
        breakdown_conn(breakdown_row())
        mock_grpc_location()
        f = client.get("/revenue/breakdown?zone_id=161").json()["filters_applied"]
        assert f["zone_name"] == "Midtown Center"
        assert f["borough"] == "Manhattan"

    def test_zone_info_null_without_zone_id(self, breakdown_conn, mock_grpc_location):
        breakdown_conn(breakdown_row())
        mock_grpc_location()
        f = client.get("/revenue/breakdown").json()["filters_applied"]
        assert f["zone_name"] is None
        assert f["borough"] is None

    def test_end_date_before_start_date_returns_400(self, breakdown_conn, mock_grpc_location):
        breakdown_conn(breakdown_row())
        mock_grpc_location()
        r = client.get("/revenue/breakdown?start_date=2015-06-01&end_date=2015-01-01")
        assert r.status_code == 400

    def test_db_error_returns_500(self, monkeypatch):
        monkeypatch.setattr("app.routers.breakdown.get_conn", lambda: (_ for _ in ()).throw(Exception("fail")))
        assert client.get("/revenue/breakdown").status_code == 500


# ---------------------------------------------------------------------------
# /revenue/fare-per-km
# ---------------------------------------------------------------------------

def fare_per_km_row(zone_id=161, avg_fare=12.0, trip_count=500):
    return {"zone_id": zone_id, "avg_fare": avg_fare, "trip_count": trip_count}


class TestFarePerKmStructure:

    def test_returns_200(self, fare_per_km_conn, mock_grpc_trip, mock_grpc_location):
        fare_per_km_conn([fare_per_km_row()])
        mock_grpc_trip()
        mock_grpc_location()
        assert client.get("/revenue/fare-per-km").status_code == 200

    def test_response_keys(self, fare_per_km_conn, mock_grpc_trip, mock_grpc_location):
        fare_per_km_conn([fare_per_km_row()])
        mock_grpc_trip()
        mock_grpc_location()
        data = client.get("/revenue/fare-per-km").json()
        assert "results" in data
        assert "filters" in data
        assert "total" in data

    def test_empty_db_returns_empty_results(self, fare_per_km_conn, mock_grpc_trip, mock_grpc_location):
        fare_per_km_conn([])
        mock_grpc_trip()
        mock_grpc_location()
        data = client.get("/revenue/fare-per-km").json()
        assert data["results"] == []
        assert data["total"] == 0

    def test_result_entry_keys(self, fare_per_km_conn, mock_grpc_trip, mock_grpc_location):
        fare_per_km_conn([fare_per_km_row()])
        mock_grpc_trip()
        mock_grpc_location()
        entry = client.get("/revenue/fare-per-km").json()["results"][0]
        for k in ("zone_id", "zone_name", "borough", "fare_per_km",
                  "avg_fare", "avg_distance_km", "trip_count"):
            assert k in entry

    def test_fare_per_km_calculated_correctly(self, fare_per_km_conn, mock_grpc_trip, mock_grpc_location):
        """avg_fare=12.0, avg_distance=5.0 → fare_per_km=2.4"""
        fare_per_km_conn([fare_per_km_row(avg_fare=12.0)])
        mock_grpc_trip()   # avg_distance=5.0
        mock_grpc_location()
        entry = client.get("/revenue/fare-per-km").json()["results"][0]
        assert entry["fare_per_km"] == round(12.0 / 5.0, 4)

    def test_zone_without_distance_excluded(self, fare_per_km_conn, mock_grpc_location, monkeypatch):
        """Zona sem distância no Trip Service deve ser excluída dos resultados."""
        fare_per_km_conn([fare_per_km_row(zone_id=161)])
        mock_grpc_location()
        stub = MagicMock()
        stub.GetDistanceByZone.return_value = MagicMock(zones=[])  # sem distâncias
        monkeypatch.setattr("app.routers.fare_per_km._get_trip_stub", lambda: stub)
        data = client.get("/revenue/fare-per-km").json()
        assert data["results"] == []
        assert data["total"] == 0


class TestFarePerKmFilters:

    def test_month_below_1_returns_422(self, fare_per_km_conn, mock_grpc_trip, mock_grpc_location):
        fare_per_km_conn([])
        mock_grpc_trip()
        mock_grpc_location()
        assert client.get("/revenue/fare-per-km?month=0").status_code == 422

    def test_month_above_12_returns_422(self, fare_per_km_conn, mock_grpc_trip, mock_grpc_location):
        fare_per_km_conn([])
        mock_grpc_trip()
        mock_grpc_location()
        assert client.get("/revenue/fare-per-km?month=13").status_code == 422

    def test_limit_below_1_returns_422(self, fare_per_km_conn, mock_grpc_trip, mock_grpc_location):
        fare_per_km_conn([])
        mock_grpc_trip()
        mock_grpc_location()
        assert client.get("/revenue/fare-per-km?limit=0").status_code == 422

    def test_filters_reflected(self, fare_per_km_conn, mock_grpc_trip, mock_grpc_location):
        fare_per_km_conn([])
        mock_grpc_trip()
        mock_grpc_location()
        f = client.get("/revenue/fare-per-km?year=2015&month=6&limit=10").json()["filters"]
        assert f["year"] == 2015 and f["month"] == 6

    def test_trip_service_grpc_error_returns_502(self, fare_per_km_conn, monkeypatch):
        fare_per_km_conn([fare_per_km_row()])
        import grpc

        class FakeRpcError(grpc.RpcError):
            def code(self): return grpc.StatusCode.UNAVAILABLE
            def details(self): return "service unavailable"

        stub = MagicMock()
        stub.GetDistanceByZone.side_effect = FakeRpcError()
        monkeypatch.setattr("app.routers.fare_per_km._get_trip_stub", lambda: stub)
        assert client.get("/revenue/fare-per-km").status_code == 502

    def test_db_error_returns_500(self, monkeypatch):
        monkeypatch.setattr("app.routers.fare_per_km.get_conn", lambda: (_ for _ in ()).throw(Exception("fail")))
        assert client.get("/revenue/fare-per-km").status_code == 500