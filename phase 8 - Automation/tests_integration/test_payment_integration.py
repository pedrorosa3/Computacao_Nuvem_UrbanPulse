"""
Testes de integração do Payment Service.
Sem mocks! Conecta diretamente ao serviço a correr via Docker.
"""
import requests

# A porta do Payment Service definida no Docker Compose é a 8006
BASE = "http://localhost:8006"

def test_payment_health():
    """Verifica se o serviço está vivo no Docker"""
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    assert r.json()["service"] == "payment-service"

def test_tips_comparison_real_data():
    """A nossa velha amiga rota das gorjetas, agora com dados reais!"""
    r = requests.get(f"{BASE}/payments/tips/comparison?start_date=2015-01-01&end_date=2015-01-31")
    assert r.status_code == 200
    data = r.json()
    
    # Aqui não forçamos um valor exato (como o 2.50), verificamos antes se a BD tem dados reais (maior que 0)
    assert data["card_average_tip_percentage"] > 0.0
    assert data["cash_average_tip_percentage"] >= 0.0
    assert "difference_points" in data

def test_payment_distribution():
    """Garante que a distribuição de métodos de pagamento (UC12) calcula totais válidos"""
    r = requests.get(f"{BASE}/payments/distribution")
    assert r.status_code == 200
    data = r.json()
    
    assert "total_trips" in data
    assert data["total_trips"] > 0
    assert "overall_distribution" in data


def test_tipping_score_real_data():
    """Garante que o ranking de zonas com melhores gorjetas (UC13) funciona com a BD real"""
    r = requests.get(f"{BASE}/payments/zones/tipping-score?limit=3")
    assert r.status_code == 200
    data = r.json()
    
    # Verifica se devolveu uma lista
    assert isinstance(data, list)
    
    # Se a BD tiver dados de 2015, a lista não deve estar vazia e deve respeitar o limite
    if len(data) > 0:
        assert len(data) <= 3
        # Verifica se as chaves corretas existem no primeiro resultado
        assert "zone_id" in data[0]
        assert "average_tip_percentage" in data[0]