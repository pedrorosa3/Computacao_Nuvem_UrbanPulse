import pytest
from unittest.mock import patch, MagicMock

# Bloqueios globais
patch("fastapi_cache.decorator.cache", lambda expire: lambda f: f).start()
patch("app.main.serve_grpc", return_value=MagicMock(stop=MagicMock())).start()

from fastapi.testclient import TestClient
from app.main import app 

client = TestClient(app)

def test_health_root():
    """Garante que a raiz do serviço responde corretamente."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "payment-service"

def test_health_payments():
    """Garante que a rota específica de health de pagamentos está ativa."""
    response = client.get("/payments/health")
    assert response.status_code == 200

def test_validation_error():
    """UC13 - Testa se o FastAPI bloqueia um limite acima do permitido (máximo 100)."""
    response = client.get("/payments/zones/tipping-score?limit=999")
    assert response.status_code == 422

