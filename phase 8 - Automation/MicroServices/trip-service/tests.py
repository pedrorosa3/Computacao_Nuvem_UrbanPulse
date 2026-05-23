import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.routers.uc01_time_of_day import classify_time
from app.routers.uc02_route_deviation import compute_deviation
from app.routers.uc03_speed_zones import compute_speed


@pytest.fixture(scope="session", autouse=True)
def mock_grpc_server():
    """Impede o servidor gRPC de arrancar durante os testes."""
    with patch("app.grpc_server.serve_grpc", return_value=MagicMock(stop=MagicMock())):
        yield


@pytest.fixture(scope="session")
def client(mock_grpc_server):
    with TestClient(app) as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "trip-service"


# ── classify_time — função pura ───────────────────────────────────────────────

def test_classify_time_peak_morning():
    assert classify_time(7) == "peak"

def test_classify_time_peak_morning_end():
    assert classify_time(9) == "peak"

def test_classify_time_peak_afternoon():
    assert classify_time(16) == "peak"

def test_classify_time_peak_afternoon_end():
    assert classify_time(19) == "peak"

def test_classify_time_night_late():
    assert classify_time(22) == "night"

def test_classify_time_night_midnight():
    assert classify_time(0) == "night"

def test_classify_time_night_early_morning():
    assert classify_time(5) == "night"

def test_classify_time_off_peak_morning():
    assert classify_time(10) == "off_peak"

def test_classify_time_off_peak_afternoon():
    assert classify_time(14) == "off_peak"

def test_classify_time_off_peak_evening():
    assert classify_time(20) == "off_peak"


# ── compute_deviation — função pura ──────────────────────────────────────────

def test_deviation_zero_distance_returns_none():
    rdi, cls = compute_deviation(0, 30)
    assert rdi is None
    assert cls is None

def test_deviation_zero_duration_returns_none():
    rdi, cls = compute_deviation(5, 0)
    assert rdi is None
    assert cls is None

def test_deviation_efficient():
    # 5 miles a 12mph = 25min esperados, real=25min → RDI=1.0
    rdi, cls = compute_deviation(5, 25)
    assert cls == "efficient"
    assert rdi <= 1.20

def test_deviation_moderate():
    # 5 miles a 12mph = 25min esperados, real=35min → RDI=1.4
    rdi, cls = compute_deviation(5, 35)
    assert cls == "moderate"
    assert 1.20 < rdi <= 1.60

def test_deviation_inefficient():
    # 5 miles a 12mph = 25min esperados, real=50min → RDI=2.0
    rdi, cls = compute_deviation(5, 50)
    assert cls == "inefficient"
    assert rdi > 1.60

def test_deviation_boundary_efficient_to_moderate():
    # RDI exatamente 1.20 → efficient
    expected = (5 / 12) * 60
    rdi, cls = compute_deviation(5, expected * 1.20)
    assert cls == "efficient"

def test_deviation_boundary_moderate_to_inefficient():
    # RDI exatamente 1.60 → moderate
    expected = (5 / 12) * 60
    rdi, cls = compute_deviation(5, expected * 1.60)
    assert cls == "moderate"


# ── compute_speed — função pura ───────────────────────────────────────────────

def test_speed_zero_distance_returns_none():
    speed, cls = compute_speed(0, 30)
    assert speed is None
    assert cls is None

def test_speed_zero_duration_returns_none():
    speed, cls = compute_speed(5, 0)
    assert speed is None
    assert cls is None

def test_speed_impossible_returns_none():
    # > 200 km/h é impossível
    speed, cls = compute_speed(100, 1)
    assert speed is None
    assert cls is None

def test_speed_slow():
    # 1 mile em 30min = ~3.2 km/h → slow
    speed, cls = compute_speed(1, 30)
    assert cls == "slow"
    assert speed < 15.0

def test_speed_normal():
    # 3 miles em 15min = ~19.3 km/h → normal
    speed, cls = compute_speed(3, 15)
    assert cls == "normal"
    assert 15.0 <= speed <= 30.0

def test_speed_fast():
    # 10 miles em 10min = ~96.6 km/h → fast
    speed, cls = compute_speed(10, 10)
    assert cls == "fast"
    assert speed > 30.0


# ── Validação de datas (sem BD) ───────────────────────────────────────────────

def test_time_of_day_end_before_start_returns_400(client):
    r = client.get("/trips/classification/time-of-day?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400

def test_route_deviation_end_before_start_returns_400(client):
    r = client.get("/trips/route-deviation?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400

def test_speed_zones_end_before_start_returns_400(client):
    r = client.get("/trips/speed/zones?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400

def test_speed_zones_invalid_period_returns_400(client):
    r = client.get("/trips/speed/zones?period=morning")
    assert r.status_code == 400


# ── Validação de parâmetros pelo FastAPI ──────────────────────────────────────

def test_route_deviation_limit_too_low_returns_422(client):
    r = client.get("/trips/route-deviation?limit=0")
    assert r.status_code == 422

def test_route_deviation_limit_too_high_returns_422(client):
    r = client.get("/trips/route-deviation?limit=101")
    assert r.status_code == 422

def test_speed_zones_limit_too_low_returns_422(client):
    r = client.get("/trips/speed/zones?limit=0")
    assert r.status_code == 422

def test_speed_zones_limit_too_high_returns_422(client):
    r = client.get("/trips/speed/zones?limit=101")
    assert r.status_code == 422


# ── UC01 com BD simulada ──────────────────────────────────────────────────────

def test_time_of_day_returns_periods(client):
    mock_rows = [
        {"period": "off_peak", "trip_count": 400, "percentage": 40.0, "total_trips": 1000},
        {"period": "peak",     "trip_count": 350, "percentage": 35.0, "total_trips": 1000},
        {"period": "night",    "trip_count": 250, "percentage": 25.0, "total_trips": 1000},
    ]
    with patch("app.routers.uc01_time_of_day.execute_query", return_value=mock_rows):
        r = client.get("/trips/classification/time-of-day")

    assert r.status_code == 200
    data = r.json()
    assert data["total_trips"] == 1000
    assert len(data["periods"]) == 3
    periods = [p["period"] for p in data["periods"]]
    assert "peak" in periods
    assert "off_peak" in periods
    assert "night" in periods

def test_time_of_day_response_field_types(client):
    mock_rows = [
        {"period": "peak", "trip_count": 500, "percentage": 50.0, "total_trips": 1000},
    ]
    with patch("app.routers.uc01_time_of_day.execute_query", return_value=mock_rows):
        r = client.get("/trips/classification/time-of-day")

    period = r.json()["periods"][0]
    assert isinstance(period["trip_count"], int)
    assert isinstance(period["percentage"], float)
