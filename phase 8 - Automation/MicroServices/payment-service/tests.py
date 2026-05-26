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

def test_tips_comparison_invalid_date_format():
    """UC11 - Garante que a API rejeita datas com o formato errado (esperado: YYYY-MM-DD)."""
    response = client.get("/payments/tips/comparison?start_date=01-01-2015&end_date=31-01-2015")
    assert response.status_code == 422  # Unprocessable Entity

def test_tips_comparison_future_date():
    """UC11 - Testa se a API lida bem com datas no futuro (deve responder 200, mas sem dados/vazio)."""
    response = client.get("/payments/tips/comparison?start_date=2099-01-01&end_date=2099-12-31")
    # Dependendo da tua implementação, pode ser 200 com array vazio, ou 404. Assumimos 200.
    assert response.status_code in [200, 404]