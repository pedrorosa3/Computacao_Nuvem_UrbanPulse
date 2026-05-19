import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.routers.uc07_zone_profile import (
    _classify_volatility,
    _classify_attractiveness,
    _compute_volatility_index,
)


@pytest.fixture(scope="session", autouse=True)
def mock_grpc_server():
    """Impede o servidor gRPC de arrancar durante os testes."""
    with patch("app.grpc_server.serve_grpc", return_value=MagicMock(stop=MagicMock())):
        yield


@pytest.fixture(scope="session")
def client(mock_grpc_server):
    with TestClient(app) as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_root(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_locations(client):
    r = client.get("/locations/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Validação de datas (sem BD) ───────────────────────────────────────────────

def test_pickup_ranking_end_before_start_returns_400(client):
    r = client.get("/locations/pickup/ranking?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400


def test_zone_profile_end_before_start_returns_400(client):
    r = client.get("/locations/1/profile?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400


# ── Lógica de negócio pura (sem BD nem gRPC) ─────────────────────────────────

def test_volatility_low():
    assert _classify_volatility(0.3) == "low"


def test_volatility_boundary_low_to_medium():
    assert _classify_volatility(0.5) == "medium"


def test_volatility_medium():
    assert _classify_volatility(1.0) == "medium"


def test_volatility_high():
    assert _classify_volatility(2.0) == "high"


def test_attractiveness_high():
    assert _classify_attractiveness(80) == "high"


def test_attractiveness_medium():
    assert _classify_attractiveness(50) == "medium"


def test_attractiveness_low():
    assert _classify_attractiveness(10) == "low"


def test_volatility_index_empty_counts_returns_default():
    vi, peak = _compute_volatility_index({})
    assert vi == 1.0
    assert peak == 0


def test_volatility_index_uniform_distribution_is_zero():
    counts = {h: 100 for h in range(24)}
    vi, _ = _compute_volatility_index(counts)
    assert vi == 0.0


# ── Endpoint com BD simulada ──────────────────────────────────────────────────

def test_pickup_ranking_returns_zones(client):
    mock_zones = [{
        "rank": 1,
        "zone_id": 161,
        "zone_name": "Midtown Center",
        "borough": "Manhattan",
        "trip_count": 500,
        "market_share_pct": 5.0,
    }]
    mock_total = [{"total": 10000}]

    with patch("app.routers.uc04_pickup_ranking.execute_query", side_effect=[mock_zones, mock_total]):
        r = client.get("/locations/pickup/ranking?limit=1")

    assert r.status_code == 200
    data = r.json()
    assert data["total_trips"] == 10000
    assert len(data["zones"]) == 1
    assert data["zones"][0]["zone_name"] == "Midtown Center"
    assert data["zones"][0]["borough"] == "Manhattan"
