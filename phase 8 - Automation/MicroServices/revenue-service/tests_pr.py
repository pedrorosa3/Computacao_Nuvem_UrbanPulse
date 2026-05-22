import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(scope="session", autouse=True)
def mock_grpc_server():
    """Impede o servidor gRPC de arrancar durante os testes."""
    with patch("app.main.grpc_serve", return_value=MagicMock(stop=MagicMock(), wait_for_termination=MagicMock())):
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

def test_avg_fare_invalid_sort_returns_422(client):
    r = client.get("/revenue/avg-fare-by-zone?sort=random")
    assert r.status_code == 422
