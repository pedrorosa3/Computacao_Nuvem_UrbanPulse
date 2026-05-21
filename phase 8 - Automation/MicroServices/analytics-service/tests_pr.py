import pytest
import grpc
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.routers.uc20_anomalous_trips import safe_float

client = TestClient(app)


class MockRpcError(grpc.RpcError):
    def code(self):    return grpc.StatusCode.UNAVAILABLE
    def details(self): return "Service unavailable"


# ── safe_float — função pura ──────────────────────────────────────────────────

def test_safe_float_normal_value():
    assert safe_float(3.14) == 3.14


def test_safe_float_nan_returns_default():
    assert safe_float(float("nan")) == 0.0


def test_safe_float_inf_returns_default():
    assert safe_float(float("inf")) == 0.0


def test_safe_float_none_returns_default():
    assert safe_float(None) == 0.0


def test_safe_float_custom_default():
    assert safe_float(None, default=-1.0) == -1.0


# ── GET /analytics/mobility-comparison ───────────────────────────────────────

def test_mobility_comparison_location_unavailable_returns_503():
    with patch("app.routers.uc19_mobility_comparison._get_zone_groups", side_effect=MockRpcError()):
        r = client.get("/analytics/mobility-comparison")
    assert r.status_code == 503


def test_mobility_comparison_returns_correct_structure():
    mock_zone_groups = MagicMock()
    mock_zone_groups.total_trips = 1000
    mock_zone_groups.affluent.zone_ids  = [1, 2]
    mock_zone_groups.affluent.zone_count = 2
    mock_zone_groups.affluent.total_trips = 700
    mock_zone_groups.affluent.market_share_pct = 70.0
    mock_zone_groups.peripheral.zone_ids  = [3]
    mock_zone_groups.peripheral.zone_count = 1
    mock_zone_groups.peripheral.total_trips = 300
    mock_zone_groups.peripheral.market_share_pct = 30.0

    mock_demand = MagicMock()
    mock_demand.peak_hour = 8
    mock_demand.avg_volatility_index = 0.5
    mock_demand.volatility_classification = "medium"

    mock_payment = MagicMock()
    mock_payment.card_payment_pct = 75.0
    mock_payment.cash_payment_pct = 25.0

    mock_revenue = MagicMock()
    mock_revenue.avg_fare = 15.0
    mock_revenue.avg_tip  = 2.5
    mock_revenue.avg_tip_pct = 16.7

    with patch("app.routers.uc19_mobility_comparison._get_zone_groups",        return_value=mock_zone_groups), \
         patch("app.routers.uc19_mobility_comparison._get_group_demand",        return_value=mock_demand), \
         patch("app.routers.uc19_mobility_comparison._get_zone_group_payment",  return_value=mock_payment), \
         patch("app.routers.uc19_mobility_comparison._get_zone_group_revenue",  return_value=mock_revenue):
        r = client.get("/analytics/mobility-comparison")

    assert r.status_code == 200
    data = r.json()
    assert "comparison" in data
    assert "affluent" in data["comparison"]
    assert "peripheral" in data["comparison"]
    assert data["total_trips"] == 1000
    assert data["comparison"]["affluent"]["trip_volume"]["total_trips"] == 700
    assert data["comparison"]["peripheral"]["trip_volume"]["total_trips"] == 300


# ── GET /analytics/duration-tip-correlation ───────────────────────────────────

def test_duration_tip_trip_service_unavailable_returns_503():
    with patch("app.routers.uc18_duration_tip._get_trip_durations", side_effect=MockRpcError()):
        r = client.get("/analytics/duration-tip-correlation")
    assert r.status_code == 503


def test_duration_tip_payment_service_unavailable_returns_503():
    mock_trip_resp = MagicMock()
    mock_trip_resp.trips = []
    with patch("app.routers.uc18_duration_tip._get_trip_durations", return_value=mock_trip_resp), \
         patch("app.routers.uc18_duration_tip._get_payment_details", side_effect=MockRpcError()):
        r = client.get("/analytics/duration-tip-correlation")
    assert r.status_code == 503


def test_duration_tip_limit_too_low_returns_422():
    r = client.get("/analytics/duration-tip-correlation?limit=9")
    assert r.status_code == 422


def test_duration_tip_limit_too_high_returns_422():
    r = client.get("/analytics/duration-tip-correlation?limit=2001")
    assert r.status_code == 422


# ── GET /analytics/anomalous-trips ───────────────────────────────────────────

def test_anomalous_trips_trip_service_unavailable_returns_503():
    with patch("app.routers.uc20_anomalous_trips._get_suspicious_trips", side_effect=MockRpcError()):
        r = client.get("/analytics/anomalous-trips")
    assert r.status_code == 503


def test_anomalous_trips_score_too_low_returns_422():
    r = client.get("/analytics/anomalous-trips?min_suspicion_score=0")
    assert r.status_code == 422


def test_anomalous_trips_score_too_high_returns_422():
    r = client.get("/analytics/anomalous-trips?min_suspicion_score=8")
    assert r.status_code == 422


def test_anomalous_trips_returns_empty_when_no_trips():
    mock_resp = MagicMock()
    mock_resp.trips = []
    mock_resp.total_found = 0
    with patch("app.routers.uc20_anomalous_trips._get_suspicious_trips", return_value=mock_resp):
        r = client.get("/analytics/anomalous-trips")
    assert r.status_code == 200
    data = r.json()
    assert data["total_found"] == 0
    assert data["trips"] == []


def test_anomalous_trips_revenue_degradation():
    """Quando o Revenue Service falha, o endpoint continua sem dados de receita."""
    mock_trip = MagicMock()
    mock_trip.trip_id = 1
    mock_trip.pickup_zone = "Midtown"
    mock_trip.dropoff_zone = "JFK"
    mock_trip.trip_distance_km = 25.0
    mock_trip.fare_amount = 52.0
    mock_trip.deviation_index = 1.5
    mock_trip.deviation_class = "inefficient"
    mock_trip.suspicion_score = 3

    mock_trips_resp = MagicMock()
    mock_trips_resp.trips = [mock_trip]
    mock_trips_resp.total_found = 1

    with patch("app.routers.uc20_anomalous_trips._get_suspicious_trips", return_value=mock_trips_resp), \
         patch("app.routers.uc20_anomalous_trips._get_trip_revenues", side_effect=MockRpcError()):
        r = client.get("/analytics/anomalous-trips")

    assert r.status_code == 200
    data = r.json()
    assert data["revenue_service_used"] is False
    assert len(data["trips"]) == 1
    assert "revenue" not in data["trips"][0]
