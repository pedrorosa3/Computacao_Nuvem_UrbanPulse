import pytest
from unittest.mock import patch, MagicMock

# BARRICADAS GLOBAIS
# Desativar a cache e o gRPC antes de importar a API para não haver engasgos
patch("fastapi_cache.decorator.cache", lambda expire: lambda f: f).start()
patch("app.main.serve_grpc", return_value=MagicMock(stop=MagicMock())).start()

from fastapi.testclient import TestClient
from app.main import app 

client = TestClient(app)

#  TESTES DE PULL REQUEST (Foco na validação e segurança da API)

def test_tipping_score_limit_too_low():
    """UC13 - Testa a proteção do endpoint. O limite mínimo é 1. Pedir 0 força erro 422."""
    response = client.get("/payments/zones/tipping-score?limit=0")
    assert response.status_code == 422

def test_tipping_score_limit_too_high():
    """UC13 - Testa a proteção do endpoint. O limite máximo é 100. Pedir 101 força erro 422."""
    response = client.get("/payments/zones/tipping-score?limit=101")
    assert response.status_code == 422

def test_tips_comparison_wrong_method():
    """UC11 - Garante que o endpoint bloqueia métodos HTTP não permitidos (ex: POST em vez de GET)."""
    response = client.post("/payments/tips/comparison")
    assert response.status_code == 405  # 405 Method Not Allowed

def test_distribution_wrong_method():
    """UC12 - Garante que o endpoint de distribuição recusa modificações indevidas."""
    response = client.delete("/payments/distribution")
    assert response.status_code == 405  # 405 Method Not Allowed


def test_tips_comparison_missing_parameters():
    """UC11 - Testa a omissão de parâmetros obrigatórios (falta a end_date)."""
    response = client.get("/payments/tips/comparison?start_date=2015-01-01")
    assert response.status_code == 422

def test_tipping_score_negative_limit():
    """UC13 - Garante que não é possível pedir um limite de zonas negativo."""
    response = client.get("/payments/zones/tipping-score?limit=-5")
    assert response.status_code == 422