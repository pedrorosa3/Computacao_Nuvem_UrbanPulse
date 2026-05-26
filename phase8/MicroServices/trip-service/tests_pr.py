import pytest
import grpc
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


class MockRpcError(grpc.RpcError):
    def code(self):    return grpc.StatusCode.UNAVAILABLE
    def details(self): return "Service unavailable"


@pytest.fixture(scope="session", autouse=True)
def mock_grpc_server():
    with patch("app.grpc_server.serve_grpc", return_value=MagicMock(stop=MagicMock())):
        yield


@pytest.fixture(scope="session")
def client(mock_grpc_server):
    with TestClient(app) as c:
        yield c


# ── UC01 — mais cenários ──────────────────────────────────────────────────────

def test_time_of_day_with_zone_filter(client):
    mock_rows = [
        {"period": "peak", "trip_count": 100, "percentage": 100.0, "total_trips": 100},
    ]
    with patch("app.routers.uc01_time_of_day.execute_query", return_value=mock_rows):
        r = client.get("/trips/classification/time-of-day?pickup_zone_id=161")
    assert r.status_code == 200
    assert r.json()["filters"]["pickup_zone_id"] == 161

def test_time_of_day_empty_result(client):
    with patch("app.routers.uc01_time_of_day.execute_query", return_value=[]):
        r = client.get("/trips/classification/time-of-day")
    assert r.status_code == 200
    assert r.json()["total_trips"] == 0
    assert r.json()["periods"] == []

def test_time_of_day_period_definitions_present(client):
    mock_rows = [
        {"period": "peak", "trip_count": 100, "percentage": 100.0, "total_trips": 100},
    ]
    with patch("app.routers.uc01_time_of_day.execute_query", return_value=mock_rows):
        r = client.get("/trips/classification/time-of-day")
    data = r.json()
    assert "period_definitions" in data
    assert "peak" in data["period_definitions"]
    assert "off_peak" in data["period_definitions"]
    assert "night" in data["period_definitions"]


# ── UC02 — mais cenários ──────────────────────────────────────────────────────

def test_route_deviation_summary_only(client):
    mock_rows = [
        {"classification": "efficient",   "trip_count": 400, "avg_rdi": 1.05, "percentage": 40.0, "total_trips": 1000},
        {"classification": "moderate",    "trip_count": 350, "avg_rdi": 1.38, "percentage": 35.0, "total_trips": 1000},
        {"classification": "inefficient", "trip_count": 250, "avg_rdi": 2.10, "percentage": 25.0, "total_trips": 1000},
    ]
    with patch("app.routers.uc02_route_deviation.execute_query", return_value=mock_rows):
        r = client.get("/trips/route-deviation?summary_only=true")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "sample_trips" not in data

def test_route_deviation_with_trips(client):
    mock_summary = [
        {"classification": "inefficient", "trip_count": 100, "avg_rdi": 2.5, "percentage": 100.0, "total_trips": 100},
    ]
    mock_trips = [{
        "id": 1, "pickup_zone_id": 161, "pickup_zone_name": "Midtown Center",
        "dropoff_zone_id": 162, "dropoff_zone_name": "Midtown East",
        "trip_distance_km": 3.2, "deviation_index": 2.5, "deviation_class": "inefficient",
    }]
    with patch("app.routers.uc02_route_deviation.execute_query", side_effect=[mock_summary, mock_trips]):
        r = client.get("/trips/route-deviation?limit=1")
    assert r.status_code == 200
    assert "sample_trips" in r.json()
    assert len(r.json()["sample_trips"]) == 1

def test_route_deviation_classification_thresholds_present(client):
    with patch("app.routers.uc02_route_deviation.execute_query", return_value=[]):
        r = client.get("/trips/route-deviation?summary_only=true")
    assert "classification_thresholds" in r.json()


# ── UC03 — mais cenários ──────────────────────────────────────────────────────

def test_speed_zones_filter_by_period(client):
    mock_rows = [{
        "zone_id": 161, "zone_name": "Midtown Center", "time_period": "peak",
        "trip_count": 100, "avg_speed_kmh": 18.5, "min_speed_kmh": 5.0,
        "max_speed_kmh": 45.0, "classification": "normal",
    }]
    with patch("app.routers.uc03_speed_zones.execute_query", return_value=mock_rows):
        r = client.get("/trips/speed/zones?period=peak")
    assert r.status_code == 200
    data = r.json()
    assert data["filters"]["period"] == "peak"
    assert len(data["zones"]) == 1
    assert data["zones"][0]["time_period"] == "peak"

def test_speed_zones_empty_result(client):
    with patch("app.routers.uc03_speed_zones.execute_query", return_value=[]):
        r = client.get("/trips/speed/zones")
    assert r.status_code == 200
    assert r.json()["total_results"] == 0

def test_speed_zones_classification_thresholds_present(client):
    with patch("app.routers.uc03_speed_zones.execute_query", return_value=[]):
        r = client.get("/trips/speed/zones")
    assert "classification_thresholds_kmh" in r.json()


# ── UC21 — DELETE ─────────────────────────────────────────────────────────────

def test_bulk_delete_dry_run(client):
    with patch("app.routers.uc21_remove_invalid.execute_query", return_value=[{"invalid_count": 47}]):
        r = client.delete("/trips/invalid/bulk?dry_run=true")
    assert r.status_code == 200
    data = r.json()
    assert data["dry_run"] is True
    assert data["invalid_trips"] == 47

def test_bulk_delete_executes(client):
    with patch("app.routers.uc21_remove_invalid.execute_query", return_value=[{"invalid_count": 10}]):
        with patch("app.routers.uc21_remove_invalid.execute_write", return_value=10):
            r = client.delete("/trips/invalid/bulk?dry_run=false")
    assert r.status_code == 200
    assert r.json()["dry_run"] is False
    assert r.json()["deleted_trips"] == 10


# ── UC22 — POST ───────────────────────────────────────────────────────────────

def test_submit_trip_valid(client):
    mock_row = {"id": 9999}
    with patch("app.routers.uc22_submit_trip.execute_write_returning", return_value=mock_row):
        r = client.post("/trips", json={
            "pickup_datetime":  "2015-01-10T08:30:00",
            "dropoff_datetime": "2015-01-10T08:55:00",
            "passenger_count": 2,
            "trip_distance_km": 5.63,
            "pickup_zone_id": 161,
            "pickup_zone_name": "Midtown Center",
            "dropoff_zone_id": 162,
            "dropoff_zone_name": "Midtown East",
            "fare_amount": 14.50,
            "tip_amount": 3.00,
            "payment_type": 1,
        })
    assert r.status_code == 201
    data = r.json()
    assert data["trip_id"] == 9999
    assert "enriched" in data
    assert data["enriched"]["time_class"] == "peak"

def test_submit_trip_dropoff_before_pickup_returns_422(client):
    r = client.post("/trips", json={
        "pickup_datetime":  "2015-01-10T09:00:00",
        "dropoff_datetime": "2015-01-10T08:00:00",
        "passenger_count": 1,
        "trip_distance_km": 3.0,
        "pickup_zone_id": 161,
        "pickup_zone_name": "Midtown Center",
        "dropoff_zone_id": 162,
        "dropoff_zone_name": "Midtown East",
        "fare_amount": 10.0,
        "payment_type": 1,
    })
    assert r.status_code == 422

def test_submit_trip_invalid_passenger_count_returns_422(client):
    r = client.post("/trips", json={
        "pickup_datetime":  "2015-01-10T08:30:00",
        "dropoff_datetime": "2015-01-10T08:55:00",
        "passenger_count": 10,
        "trip_distance_km": 3.0,
        "pickup_zone_id": 161,
        "pickup_zone_name": "Midtown Center",
        "dropoff_zone_id": 162,
        "dropoff_zone_name": "Midtown East",
        "fare_amount": 10.0,
        "payment_type": 1,
    })
    assert r.status_code == 422

def test_submit_trip_enriched_fields_computed(client):
    mock_row = {"id": 1}
    with patch("app.routers.uc22_submit_trip.execute_write_returning", return_value=mock_row):
        r = client.post("/trips", json={
            "pickup_datetime":  "2015-01-10T22:30:00",
            "dropoff_datetime": "2015-01-10T23:00:00",
            "passenger_count": 1,
            "trip_distance_km": 3.2,
            "pickup_zone_id": 161,
            "pickup_zone_name": "Midtown Center",
            "dropoff_zone_id": 162,
            "dropoff_zone_name": "Midtown East",
            "fare_amount": 12.0,
            "payment_type": 2,
        })
    assert r.status_code == 201
    enriched = r.json()["enriched"]
    assert enriched["time_class"] == "night"
    assert enriched["deviation_class"] in ["efficient", "moderate", "inefficient"]
    assert enriched["speed_class"] in ["slow", "normal", "fast"]
    assert isinstance(enriched["suspicion_score"], int)
