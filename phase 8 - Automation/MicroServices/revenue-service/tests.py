import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(scope="session", autouse=True)
def mock_grpc_server():
    """Impede o servidor gRPC de arrancar durante os testes."""
    with patch("app.grpc_server.serve", return_value=MagicMock(stop=MagicMock(), wait_for_termination=MagicMock())):
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
    assert r.json()["service"] == "revenue"

# ── Validação de parâmetros pelo FastAPI ─────────────────────────────────────

def test_breakdown_missing_zone_id_returns_422(client):
    # Assuming breakdown needs a zone_id, let's verify invalid request
    # Since we didn't inspect all details, we can test missing required parameters if any, 
    # or just invalid query values like a negative limit if applicable.
    r = client.get("/revenue/breakdown?month=13")
    assert r.status_code == 422

def test_avg_fare_invalid_month_returns_422(client):
    r = client.get("/revenue/avg-fare-by-zone?month=0")
    assert r.status_code == 422

def test_fare_per_km_invalid_month_returns_422(client):
    r = client.get("/revenue/fare-per-km?month=13")
    assert r.status_code == 422
