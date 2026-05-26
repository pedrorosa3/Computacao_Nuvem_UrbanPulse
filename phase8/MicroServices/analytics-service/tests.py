import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_root():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "analytics"


def test_health_analytics():
    r = client.get("/analytics/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "analytics"


# ── Endpoints de infra ────────────────────────────────────────────────────────

def test_metrics_endpoint():
    r = client.get("/analytics/metrics")
    assert r.status_code == 200


def test_openapi_endpoint():
    r = client.get("/analytics/openapi.json")
    assert r.status_code == 200


def test_docs_endpoint():
    r = client.get("/analytics/docs")
    assert r.status_code == 200


# ── Validação de parâmetros — /analytics/duration-tip-correlation ─────────────

def test_duration_tip_limit_too_low_returns_422():
    r = client.get("/analytics/duration-tip-correlation?limit=9")
    assert r.status_code == 422


def test_duration_tip_limit_too_high_returns_422():
    r = client.get("/analytics/duration-tip-correlation?limit=2001")
    assert r.status_code == 422


def test_duration_tip_limit_minimum_accepted():
    r = client.get("/analytics/duration-tip-correlation?limit=10")
    assert r.status_code in (200, 503)


def test_duration_tip_limit_maximum_accepted():
    r = client.get("/analytics/duration-tip-correlation?limit=2000")
    assert r.status_code in (200, 503)


# ── Validação de parâmetros — /analytics/anomalous-trips ─────────────────────

def test_anomalous_trips_score_too_low_returns_422():
    r = client.get("/analytics/anomalous-trips?min_suspicion_score=0")
    assert r.status_code == 422


def test_anomalous_trips_score_too_high_returns_422():
    r = client.get("/analytics/anomalous-trips?min_suspicion_score=8")
    assert r.status_code == 422


def test_anomalous_trips_limit_too_low_returns_422():
    r = client.get("/analytics/anomalous-trips?limit=0")
    assert r.status_code == 422


def test_anomalous_trips_limit_too_high_returns_422():
    r = client.get("/analytics/anomalous-trips?limit=201")
    assert r.status_code == 422


def test_anomalous_trips_score_minimum_accepted():
    r = client.get("/analytics/anomalous-trips?min_suspicion_score=1")
    assert r.status_code in (200, 503)


def test_anomalous_trips_score_maximum_accepted():
    r = client.get("/analytics/anomalous-trips?min_suspicion_score=7")
    assert r.status_code in (200, 503)
