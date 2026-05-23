import pytest
import grpc
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.routers.uc_zones import classify_zone


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


# ── classify_zone — função pura ───────────────────────────────────────────────

def test_classify_zone_affluent():
    assert classify_zone("Manhattan", "Yellow Zone") == "affluent"


def test_classify_zone_peripheral_bronx():
    assert classify_zone("Bronx", "Boro Zone") == "peripheral"


def test_classify_zone_peripheral_staten_island():
    assert classify_zone("Staten Island", "Other Zone") == "peripheral"


def test_classify_zone_peripheral_boro_zone():
    assert classify_zone("Queens", "Boro Zone") == "peripheral"


def test_classify_zone_other():
    assert classify_zone("Queens", "Airport") == "other"


# ── GET /locations/zones — BD simulada ───────────────────────────────────────

def test_zones_returns_list_with_classifications(client):
    mock_rows = [
        {"location_id": 161, "zone_name": "Midtown Center",            "borough": "Manhattan", "service_zone": "Yellow Zone"},
        {"location_id": 3,   "zone_name": "Allerton/Pelham Gardens",   "borough": "Bronx",     "service_zone": "Boro Zone"},
        {"location_id": 138, "zone_name": "LaGuardia Airport",         "borough": "Queens",    "service_zone": "Airport"},
    ]
    with patch("app.routers.uc_zones.execute_query", return_value=mock_rows):
        r = client.get("/locations/zones")

    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    assert data[0]["classification"] == "affluent"
    assert data[1]["classification"] == "peripheral"
    assert data[2]["classification"] == "other"


# ── GET /locations/{zone_id}/dropoffs ─────────────────────────────────────────

def test_dropoffs_invalid_dates_returns_400(client):
    r = client.get("/locations/161/dropoffs?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400


def test_dropoffs_limit_too_high_returns_422(client):
    r = client.get("/locations/161/dropoffs?limit=51")
    assert r.status_code == 422


def test_dropoffs_zone_not_found_returns_404(client):
    with patch("app.routers.uc05_dropoffs.execute_query", return_value=[]):
        r = client.get("/locations/9999/dropoffs")
    assert r.status_code == 404


def test_dropoffs_returns_correct_structure(client):
    mock_zone     = [{"location_id": 161, "zone_name": "Midtown Center", "borough": "Manhattan"}]
    mock_total    = [{"total": 500}]
    mock_dropoffs = [{
        "rank": 1, "zone_id": 162, "zone_name": "Midtown East",
        "borough": "Manhattan", "trip_count": 100, "destination_share_pct": 20.0,
    }]
    with patch("app.routers.uc05_dropoffs.execute_query", side_effect=[mock_zone, mock_total, mock_dropoffs]):
        r = client.get("/locations/161/dropoffs?limit=1")

    assert r.status_code == 200
    data = r.json()
    assert data["origin_zone"]["zone_id"] == 161
    assert data["origin_zone"]["total_trips_from_zone"] == 500
    assert len(data["dropoffs"]) == 1
    assert data["dropoffs"][0]["zone_name"] == "Midtown East"


# ── GET /locations/pairs ──────────────────────────────────────────────────────

def test_od_pairs_invalid_dates_returns_400(client):
    r = client.get("/locations/pairs?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400


def test_od_pairs_limit_too_high_returns_422(client):
    r = client.get("/locations/pairs?limit=101")
    assert r.status_code == 422


def test_od_pairs_returns_correct_structure(client):
    mock_total = [{"total": 10000}]
    mock_pairs = [{
        "rank": 1,
        "origin_zone_id": 161,      "origin_zone_name": "Midtown Center",
        "origin_borough": "Manhattan",
        "destination_zone_id": 162, "destination_zone_name": "Midtown East",
        "destination_borough": "Manhattan",
        "trip_count": 500, "affinity_index": 1.5, "relative_frequency_pct": 5.0,
    }]
    with patch("app.routers.uc06_od_pairs.execute_query", side_effect=[mock_total, mock_pairs]):
        r = client.get("/locations/pairs?limit=1")

    assert r.status_code == 200
    data = r.json()
    assert data["total_trips"] == 10000
    assert len(data["pairs"]) == 1
    assert data["pairs"][0]["origin_zone_name"] == "Midtown Center"
    assert data["pairs"][0]["destination_zone_name"] == "Midtown East"
