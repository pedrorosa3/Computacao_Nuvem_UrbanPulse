import requests

BASE = "http://localhost:8002"

# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    assert r.json()["service"] == "demand"

# ── Endpoints ─────────────────────────────────────────────────────────────────

def test_hourly_matrix_returns_200():
    r = requests.get(f"{BASE}/demand/hourly-matrix")
    assert r.status_code == 200
    data = r.json()
    assert "matrix" in data

def test_monthly_trend_returns_200():
    r = requests.get(f"{BASE}/demand/monthly-trend")
    assert r.status_code == 200
    data = r.json()
    assert "trend" in data

def test_volatility_missing_zone_returns_422():
    r = requests.get(f"{BASE}/demand/zone-volatility")
    assert r.status_code == 422

def test_volatility_real_zone():
    r = requests.get(f"{BASE}/demand/zone-volatility?zone_id=161")
    # Even if no data, it handles it gracefully based on code
    assert r.status_code == 200
