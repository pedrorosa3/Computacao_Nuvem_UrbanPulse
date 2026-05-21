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
