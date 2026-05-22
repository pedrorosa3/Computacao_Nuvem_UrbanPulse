import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

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
    assert r.json()["service"] == "demand"

# ── Validação de parâmetros pelo FastAPI ─────────────────────────────────────

def test_volatility_missing_zone_id_returns_422(client):
    # UC17 requires zone_id
    r = client.get("/demand/zone-volatility")
    assert r.status_code == 422

def test_volatility_invalid_month_returns_422(client):
    r = client.get("/demand/zone-volatility?zone_id=161&month=13")
    assert r.status_code == 422

def test_monthly_trend_invalid_month_returns_422(client):
    r = client.get("/demand/monthly-trend?month=0")
    assert r.status_code == 422

def test_hourly_matrix_invalid_month_returns_422(client):
    r = client.get("/demand/hourly-matrix?month=15")
    assert r.status_code == 422
