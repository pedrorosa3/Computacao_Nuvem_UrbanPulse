import time
import pytest
import requests

SERVICES = {
    "location":  "http://localhost:8000/health",
    "trip":      "http://localhost:8001/trips/health",
    "demand":    "http://localhost:8002/health",
    "analytics": "http://localhost:8003/analytics/health",
    "payment":   "http://localhost:8006/health",
    "revenue":   "http://localhost:8007/health",
}


def wait_for(name, url, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=3).status_code == 200:
                print(f"✅ {name} ready")
                return
        except Exception:
            pass
        time.sleep(3)
    raise TimeoutError(f"{name} ({url}) not ready after {timeout}s")


@pytest.fixture(scope="session", autouse=True)
def wait_for_all_services():
    for name, url in SERVICES.items():
        wait_for(name, url)
