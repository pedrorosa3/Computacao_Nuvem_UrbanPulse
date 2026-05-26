"""
Testes de integração do Analytics Service.

O Analytics é um orquestrador que agrega dados de todos os outros serviços via gRPC.
Estes testes verificam que:
  - Todos os endpoints retornam 200
  - Os dados de cada serviço externo chegaram realmente (não são None)
  - Location, Demand, Payment e Revenue respondem via gRPC com dados reais
  - Trip responde via gRPC com dados reais
"""
import requests

BASE = "http://localhost:8003"


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    assert r.json()["service"] == "analytics"


def test_analytics_health():
    r = requests.get(f"{BASE}/analytics/health")
    assert r.status_code == 200
    assert r.json()["service"] == "analytics"


# ── GET /analytics/mobility-comparison ───────────────────────────────────────
# Verifica: Location gRPC, Demand gRPC, Payment gRPC, Revenue gRPC

def test_mobility_comparison_returns_200():
    r = requests.get(f"{BASE}/analytics/mobility-comparison")
    assert r.status_code == 200


def test_mobility_comparison_location_grpc_responded():
    """Location Service respondeu via gRPC — total_trips vem de GetZoneGroups."""
    r = requests.get(f"{BASE}/analytics/mobility-comparison")
    data = r.json()
    assert data["total_trips"] > 0
    assert data["comparison"]["affluent"]["zone_count"] > 0
    assert data["comparison"]["peripheral"]["zone_count"] > 0


def test_mobility_comparison_demand_grpc_responded():
    """Demand Service respondeu via gRPC — demand não pode ser None."""
    r = requests.get(f"{BASE}/analytics/mobility-comparison")
    data = r.json()
    affluent_demand   = data["comparison"]["affluent"]["demand"]
    peripheral_demand = data["comparison"]["peripheral"]["demand"]
    assert affluent_demand is not None, "Demand Service não respondeu para zonas affluent"
    assert peripheral_demand is not None, "Demand Service não respondeu para zonas peripheral"
    assert "peak_hour" in affluent_demand
    assert "volatility_classification" in affluent_demand


def test_mobility_comparison_payment_grpc_responded():
    """Payment Service respondeu via gRPC — card_payment_pct não pode ser None."""
    r = requests.get(f"{BASE}/analytics/mobility-comparison")
    data = r.json()
    affluent_payments   = data["comparison"]["affluent"]["payments"]
    peripheral_payments = data["comparison"]["peripheral"]["payments"]
    assert affluent_payments["card_payment_pct"] is not None, "Payment Service não respondeu para zonas affluent"
    assert peripheral_payments["card_payment_pct"] is not None, "Payment Service não respondeu para zonas peripheral"
    assert affluent_payments["cash_payment_pct"] is not None


def test_mobility_comparison_revenue_grpc_responded():
    """Revenue Service respondeu via gRPC — avg_fare não pode ser None."""
    r = requests.get(f"{BASE}/analytics/mobility-comparison")
    data = r.json()
    affluent_financials   = data["comparison"]["affluent"]["financials"]
    peripheral_financials = data["comparison"]["peripheral"]["financials"]
    assert affluent_financials["avg_fare"] is not None, "Revenue Service não respondeu para zonas affluent"
    assert peripheral_financials["avg_fare"] is not None, "Revenue Service não respondeu para zonas peripheral"
    assert affluent_financials["avg_tip"] is not None


def test_mobility_comparison_complete_structure():
    """Verifica a estrutura completa da resposta com dados de todos os serviços."""
    r = requests.get(f"{BASE}/analytics/mobility-comparison")
    data = r.json()
    for group in ["affluent", "peripheral"]:
        g = data["comparison"][group]
        assert g["zone_count"] > 0
        assert g["trip_volume"]["total_trips"] >= 0
        assert g["demand"] is not None
        assert g["payments"]["card_payment_pct"] is not None
        assert g["financials"]["avg_fare"] is not None


# ── GET /analytics/duration-tip-correlation ───────────────────────────────────
# Verifica: Trip gRPC (GetTripDurations) e Payment gRPC (GetPaymentDetails)

def test_duration_tip_returns_200():
    r = requests.get(f"{BASE}/analytics/duration-tip-correlation?limit=100")
    assert r.status_code == 200


def test_duration_tip_trip_and_payment_grpc_responded():
    """Trip e Payment responderam via gRPC com dados reais."""
    r = requests.get(f"{BASE}/analytics/duration-tip-correlation?limit=100")
    data = r.json()
    assert "by_period" in data
    assert "total_trips_analysed" in data
    assert "global_pearson_correlation" in data
    assert data["total_trips_analysed"] > 0, "Nenhuma viagem com pagamento por cartão — verifica os seeds"


def test_duration_tip_invalid_limit_too_low():
    assert requests.get(f"{BASE}/analytics/duration-tip-correlation?limit=9").status_code == 422


def test_duration_tip_invalid_limit_too_high():
    assert requests.get(f"{BASE}/analytics/duration-tip-correlation?limit=2001").status_code == 422


# ── GET /analytics/anomalous-trips ───────────────────────────────────────────
# Verifica: Trip gRPC (GetSuspiciousTrips) e Revenue gRPC (GetTripRevenues)

def test_anomalous_trips_returns_200():
    r = requests.get(f"{BASE}/analytics/anomalous-trips?min_suspicion_score=1")
    assert r.status_code == 200


def test_anomalous_trips_trip_grpc_responded():
    """Trip Service respondeu via gRPC — score_distribution deve estar presente."""
    r = requests.get(f"{BASE}/analytics/anomalous-trips?min_suspicion_score=1")
    data = r.json()
    assert "total_found" in data
    assert "score_distribution" in data
    dist = data["score_distribution"]
    assert "low" in dist
    assert "high" in dist
    assert "critical" in dist


def test_anomalous_trips_revenue_grpc_responded():
    """Revenue Service respondeu via gRPC — revenue_service_used deve ser True.

    Só é verificável quando existem viagens suspeitas — sem elas o endpoint
    retorna cedo e não chega a chamar o Revenue Service.
    """
    r = requests.get(f"{BASE}/analytics/anomalous-trips?min_suspicion_score=1")
    data = r.json()
    assert data["total_found"] > 0, "Nenhuma viagem suspeita no seed — suspicion_score >= 1 esperado"
    assert data["revenue_service_used"] is True, "Revenue Service não respondeu via gRPC"


def test_anomalous_trips_filters_work():
    r = requests.get(f"{BASE}/analytics/anomalous-trips?min_suspicion_score=4")
    data = r.json()
    for trip in data["trips"]:
        assert trip["suspicion_score"] >= 4


def test_anomalous_trips_invalid_score_too_low():
    assert requests.get(f"{BASE}/analytics/anomalous-trips?min_suspicion_score=0").status_code == 422


def test_anomalous_trips_invalid_score_too_high():
    assert requests.get(f"{BASE}/analytics/anomalous-trips?min_suspicion_score=8").status_code == 422


# ── Acceptance Tests ──────────────────────────────────────────────────────────
# Verificam que o sistema cumpre os requisitos de negócio prometidos ao utilizador.

def test_mobility_comparison_zone_classifications_fixed():
    """Requisito: as classificações de zonas são fixas e conhecidas."""
    r = requests.get(f"{BASE}/analytics/mobility-comparison")
    classifications = r.json()["zone_classifications"]
    assert classifications["affluent"] == "Manhattan Yellow Zone"
    assert classifications["peripheral"] == "Bronx, Staten Island and Boro Zones"


def test_mobility_comparison_affluent_dominates_market():
    """Requisito de negócio: zonas affluent (Manhattan) têm maior quota de mercado."""
    r = requests.get(f"{BASE}/analytics/mobility-comparison")
    data = r.json()["comparison"]
    affluent_share   = data["affluent"]["trip_volume"]["market_share_pct"]
    peripheral_share = data["peripheral"]["trip_volume"]["market_share_pct"]
    assert affluent_share > peripheral_share, "Manhattan deve ter maior quota de mercado"


def test_mobility_comparison_market_share_in_range():
    """Requisito: market_share_pct está entre 0 e 100 para ambos os grupos."""
    r = requests.get(f"{BASE}/analytics/mobility-comparison")
    data = r.json()["comparison"]
    for group in ["affluent", "peripheral"]:
        share = data[group]["trip_volume"]["market_share_pct"]
        assert 0 <= share <= 100


def test_mobility_gap_direction_correct():
    """Requisito: mobility gap é positivo quando affluent tem mais quota que peripheral."""
    r = requests.get(f"{BASE}/analytics/mobility-comparison")
    data = r.json()
    gap_key = "mobility_gap (Zonas Peripheral VS Affluent - Tudo em %)"
    gap = data[gap_key]["trip_volume_gap_pct"]
    affluent   = data["comparison"]["affluent"]["trip_volume"]["market_share_pct"]
    peripheral = data["comparison"]["peripheral"]["trip_volume"]["market_share_pct"]
    if affluent > peripheral:
        assert gap > 0, "Gap deve ser positivo quando affluent domina o mercdo"


def test_anomalous_trips_labels_follow_business_rule():
    """Requisito: labels de anomalia seguem a regra de negócio definida.

    low = score 1 | high = score 2-3 | critical = score >= 4
    """
    r = requests.get(f"{BASE}/analytics/anomalous-trips?min_suspicion_score=1&limit=50")
    for trip in r.json()["trips"]:
        score = trip["suspicion_score"]
        label = trip["anomaly_label"]
        if score >= 4:
            assert label == "critical", f"Score {score} devia ser critical, got {label}"
        elif score >= 2:
            assert label == "high", f"Score {score} devia ser high, got {label}"
        else:
            assert label == "low", f"Score {score} devia ser low, got {label}"


def test_duration_tip_periods_are_valid():
    """Requisito: períodos devolvidos são apenas peak, off_peak ou night."""
    r = requests.get(f"{BASE}/analytics/duration-tip-correlation?limit=100")
    for period_data in r.json()["by_period"]:
        assert period_data["period"] in ["peak", "off_peak", "night"]