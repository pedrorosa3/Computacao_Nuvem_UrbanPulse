import requests

BASE = "http://localhost:8000"


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_locations_health():
    r = requests.get(f"{BASE}/locations/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── GET /locations/zones ──────────────────────────────────────────────────────

def test_zones_all_loaded():
    r = requests.get(f"{BASE}/locations/zones")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 260
    classifications = {z["classification"] for z in data}
    assert classifications == {"affluent", "peripheral", "other"}


# ── GET /locations/pickup/ranking ─────────────────────────────────────────────

def test_pickup_ranking_returns_real_data():
    r = requests.get(f"{BASE}/locations/pickup/ranking")
    assert r.status_code == 200
    data = r.json()
    assert data["total_trips"] > 0
    assert len(data["zones"]) > 0
    assert data["zones"][0]["trip_count"] > 0


def test_pickup_ranking_limit_respected():
    r = requests.get(f"{BASE}/locations/pickup/ranking?limit=3")
    assert r.status_code == 200
    assert len(r.json()["zones"]) <= 3


def test_pickup_ranking_period_returned():
    r = requests.get(f"{BASE}/locations/pickup/ranking?start_date=2015-01-01&end_date=2015-01-31")
    assert r.status_code == 200
    data = r.json()
    assert data["period"]["start_date"] == "2015-01-01"
    assert data["period"]["end_date"] == "2015-01-31"


def test_pickup_ranking_invalid_dates():
    r = requests.get(f"{BASE}/locations/pickup/ranking?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400


def test_pickup_ranking_invalid_limit():
    assert requests.get(f"{BASE}/locations/pickup/ranking?limit=0").status_code == 422
    assert requests.get(f"{BASE}/locations/pickup/ranking?limit=51").status_code == 422


# ── GET /locations/{zone_id}/profile ─────────────────────────────────────────

def test_zone_profile_real_zone():
    r = requests.get(f"{BASE}/locations/161/profile")
    assert r.status_code == 200
    data = r.json()
    assert data["zone_id"] == 161
    assert data["zone_name"] == "Midtown Center"
    assert "trip_volume" in data
    assert "financials" in data
    assert "attractiveness_score" in data


def test_zone_profile_demand_grpc_responded():
    """Location Service chama Demand Service via gRPC — demand_patterns não pode ser None."""
    r = requests.get(f"{BASE}/locations/161/profile")
    data = r.json()
    assert data["demand_patterns"] is not None, "Demand Service não respondeu via gRPC ao Location"
    assert "peak_hour" in data["demand_patterns"]
    assert "volatility_index" in data["demand_patterns"]
    assert "volatility_classification" in data["demand_patterns"]


def test_zone_profile_not_found():
    r = requests.get(f"{BASE}/locations/9999/profile")
    assert r.status_code == 404


def test_zone_profile_invalid_dates():
    r = requests.get(f"{BASE}/locations/161/profile?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400


# ── GET /locations/{zone_id}/dropoffs ─────────────────────────────────────────

def test_dropoffs_real_zone():
    r = requests.get(f"{BASE}/locations/161/dropoffs")
    assert r.status_code == 200
    data = r.json()
    assert data["origin_zone"]["zone_id"] == 161
    assert "dropoffs" in data
    assert data["origin_zone"]["total_trips_from_zone"] > 0


def test_dropoffs_zone_not_found():
    r = requests.get(f"{BASE}/locations/9999/dropoffs")
    assert r.status_code == 404


def test_dropoffs_invalid_dates():
    r = requests.get(f"{BASE}/locations/161/dropoffs?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400


# ── GET /locations/pairs ──────────────────────────────────────────────────────

def test_od_pairs_returns_data():
    r = requests.get(f"{BASE}/locations/pairs?min_trips=1&limit=5")
    assert r.status_code == 200
    data = r.json()
    assert data["total_trips"] > 0
    assert len(data["pairs"]) > 0
    assert "origin_zone_name" in data["pairs"][0]
    assert "destination_zone_name" in data["pairs"][0]


def test_od_pairs_invalid_dates():
    r = requests.get(f"{BASE}/locations/pairs?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400


# ── Acceptance Tests ──────────────────────────────────────────────────────────
# Verificam que o sistema cumpre os requisitos de negócio prometidos ao utilizador.

def test_pickup_ranking_sorted_by_trip_count():
    """Requisito: zonas devolvidas ordenadas por número de viagens (desc)."""
    r = requests.get(f"{BASE}/locations/pickup/ranking?limit=10")
    counts = [z["trip_count"] for z in r.json()["zones"]]
    assert counts == sorted(counts, reverse=True)


def test_pickup_ranking_ranks_are_sequential():
    """Requisito: ranks são sequenciais a partir de 1."""
    r = requests.get(f"{BASE}/locations/pickup/ranking?limit=5")
    ranks = [z["rank"] for z in r.json()["zones"]]
    assert ranks == list(range(1, len(ranks) + 1))


def test_pickup_ranking_market_share_positive():
    """Requisito: market_share_pct é positivo para todas as zonas devolvidas."""
    r = requests.get(f"{BASE}/locations/pickup/ranking?limit=5")
    for zone in r.json()["zones"]:
        assert zone["market_share_pct"] > 0


def test_zone_profile_attractiveness_score_in_range():
    """Requisito: attractiveness_score está entre 0 e 100."""
    r = requests.get(f"{BASE}/locations/161/profile")
    score = r.json()["attractiveness_score"]
    assert 0 <= score <= 100


def test_zone_profile_attractiveness_classification_valid():
    """Requisito: attractiveness_classification é low, medium ou high."""
    r = requests.get(f"{BASE}/locations/161/profile")
    classification = r.json()["attractiveness_classification"]
    assert classification in ["low", "medium", "high"]


def test_zone_profile_volatility_classification_valid():
    """Requisito: volatility_classification é low, medium ou high."""
    r = requests.get(f"{BASE}/locations/161/profile")
    demand = r.json()["demand_patterns"]
    if demand:
        assert demand["volatility_classification"] in ["low", "medium", "high"]


def test_dropoffs_sorted_by_trip_count():
    """Requisito: dropoffs ordenados por número de viagens (desc)."""
    r = requests.get(f"{BASE}/locations/161/dropoffs?limit=10")
    counts = [d["trip_count"] for d in r.json()["dropoffs"]]
    assert counts == sorted(counts, reverse=True)


def test_od_pairs_affinity_index_positive():
    """Requisito: affinity_index é sempre positivo."""
    r = requests.get(f"{BASE}/locations/pairs?min_trips=1&limit=5")
    for pair in r.json()["pairs"]:
        assert pair["affinity_index"] > 0


def test_od_pairs_relative_frequency_in_range():
    """Requisito: relative_frequency_pct está entre 0 e 100."""
    r = requests.get(f"{BASE}/locations/pairs?min_trips=1&limit=5")
    for pair in r.json()["pairs"]:
        assert 0 < pair["relative_frequency_pct"] <= 100