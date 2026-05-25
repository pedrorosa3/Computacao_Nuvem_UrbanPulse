import pytest
from unittest.mock import patch, MagicMock

# 1. BLOQUEAR TUDO ANTES DE IMPORTAR A APP
# Removemos o decorador @cache para não precisar de inicialização
patch("fastapi_cache.decorator.cache", lambda expire: lambda f: f).start()

# Classes e dados simulados
class MockRow:
    def __init__(self, payment_type, avg_tip_pct):
        self.payment_type = payment_type
        self.avg_tip_pct = avg_tip_pct

mock_rows = [MockRow("card", 2.50), MockRow("cash", 0.50)]
mock_query = MagicMock()
mock_query.filter.return_value = mock_query
mock_query.group_by.return_value = mock_query
mock_query.all.return_value = mock_rows

mock_session = MagicMock()
mock_session.query.return_value = mock_query

# Aplicar os bloqueios globais
patch("app.database.SessionLocal", return_value=mock_session).start()
patch("app.main.serve_grpc", return_value=MagicMock(stop=MagicMock())).start()

# 2. Importar a API
from fastapi.testclient import TestClient
from app.main import app 

client = TestClient(app)

# 3. Os Testes
def test_health_root():
    response = client.get("/health")
    assert response.status_code == 200

def test_health_payments():
    response = client.get("/payments/health")
    assert response.status_code == 200

def test_validation_error():
    response = client.get("/payments/zones/tipping-score?limit=999")
    assert response.status_code == 422

def test_tips_comparison_success():
    # Agora, sem o decorador de cache a interferir, vai correr limpo
    response = client.get("/payments/tips/comparison?start_date=2015-01-01&end_date=2015-01-31")
    assert response.status_code == 200
    assert response.json()["card_average_tip_percentage"] == 2.50
    assert response.json()["cash_average_tip_percentage"] == 0.50
    assert response.json()["difference_points"] == 2.0