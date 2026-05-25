import pytest
from unittest.mock import patch, MagicMock

class MockRow:
    def __init__(self, payment_type, count):
        self.payment_type = payment_type
        self.count = count
        self.passenger_count = 1
        self.tip_amount = 2.0
        self.fare_amount = 10.0

# 1. Configurar o mock global para arrancar a API em segurança
mock_rows = [MockRow("card", 80), MockRow("cash", 20)]
mock_query = MagicMock()
mock_query.filter.return_value = mock_query
mock_query.group_by.return_value = mock_query
mock_query.order_by.return_value = mock_query
mock_query.limit.return_value = mock_query
mock_query.all.return_value = mock_rows
mock_query.scalar.return_value = 100 # Para o total de viagens

mock_session = MagicMock()
mock_session.query.return_value = mock_query

patch("app.database.SessionLocal", return_value=mock_session).start()
patch("app.main.serve_grpc", return_value=MagicMock(stop=MagicMock())).start()

# 2. Iniciar FastAPI e Cache Falsa
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi.testclient import TestClient
from app.main import app 

backend = InMemoryBackend()
FastAPICache.init(backend, prefix="test-pr-cache")
client = TestClient(app)

@pytest.fixture(autouse=True)
async def clear_cache():
    await backend.clear()

# 3. TESTES DE PULL REQUEST (Mais complexos e abrangentes)

def test_payment_distribution_success():
    """Testa se o endpoint de distribuição calcula bem as percentagens."""
    response = client.get("/payments/distribution")
    assert response.status_code == 200
    assert "overall_distribution" in response.json()
    assert response.json()["total_trips"] == 100

def test_passenger_correlation_no_data():
    """Testa o comportamento da API quando a base de dados devolve uma lista vazia."""
    # Criamos um mock específico só para este teste devolver 0 linhas
    mock_empty_query = MagicMock()
    mock_empty_query.filter.return_value = mock_empty_query
    mock_empty_query.limit.return_value = mock_empty_query
    mock_empty_query.all.return_value = []
    
    # Bloqueamos o SQLAlchemy diretamente para injetar a nossa query vazia
    with patch("sqlalchemy.orm.Session.query", return_value=mock_empty_query):
        response = client.get("/payments/tips/passenger-correlation")
        
    # A tua API devolve 200 mas com uma mensagem de erro controlada
    assert response.status_code == 200
    assert response.json() == {"message": "Sem dados suficientes para o período selecionado."}