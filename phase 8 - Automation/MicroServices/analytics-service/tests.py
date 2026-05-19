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
