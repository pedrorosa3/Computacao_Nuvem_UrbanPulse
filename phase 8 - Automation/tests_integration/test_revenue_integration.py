import requests

BASE = "http://localhost:8007"

# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    assert r.json()["service"] == "revenue"

# ── Endpoints ─────────────────────────────────────────────────────────────────

def test_avg_fare_returns_200():
    r = requests.get(f"{BASE}/revenue/avg-fare-by-zone")
    assert r.status_code == 200

def test_breakdown_returns_200():
    r = requests.get(f"{BASE}/revenue/breakdown")
    assert r.status_code == 200

def test_fare_per_km_returns_200():
    r = requests.get(f"{BASE}/revenue/fare-per-km")
    assert r.status_code == 200
