import requests

BASE = "http://localhost:8001"


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "trip-service"


# ── UC01 — GET /trips/classification/time-of-day ──────────────────────────────

def test_time_of_day_returns_200():
    r = requests.get(f"{BASE}/trips/classification/time-of-day")
    assert r.status_code == 200

def test_time_of_day_has_real_data():
    r = requests.get(f"{BASE}/trips/classification/time-of-day")
    data = r.json()
    assert data["total_trips"] > 0
    assert len(data["periods"]) > 0

def test_time_of_day_all_periods_present():
    r = requests.get(f"{BASE}/trips/classification/time-of-day")
    periods = [p["period"] for p in r.json()["periods"]]
    assert "peak" in periods
    assert "off_peak" in periods
    assert "night" in periods

def test_time_of_day_percentages_sum_to_100():
    r = requests.get(f"{BASE}/trips/classification/time-of-day")
    total_pct = sum(p["percentage"] for p in r.json()["periods"])
    assert abs(total_pct - 100.0) < 0.1

def test_time_of_day_with_date_filter():
    r = requests.get(f"{BASE}/trips/classification/time-of-day?start_date=2015-01-01&end_date=2015-01-15")
    assert r.status_code == 200
    data = r.json()
    assert data["filters"]["start_date"] == "2015-01-01"
    assert data["filters"]["end_date"] == "2015-01-15"

def test_time_of_day_invalid_dates_returns_400():
    r = requests.get(f"{BASE}/trips/classification/time-of-day?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400


# ── UC02 — GET /trips/route-deviation ─────────────────────────────────────────

def test_route_deviation_returns_200():
    r = requests.get(f"{BASE}/trips/route-deviation?summary_only=true")
    assert r.status_code == 200

def test_route_deviation_has_real_data():
    r = requests.get(f"{BASE}/trips/route-deviation?summary_only=true")
    data = r.json()
    assert data["total_trips_analysed"] > 0
    assert len(data["summary"]) > 0

def test_route_deviation_classifications_present():
    r = requests.get(f"{BASE}/trips/route-deviation?summary_only=true")
    classifications = [s["classification"] for s in r.json()["summary"]]
    assert "efficient" in classifications or "moderate" in classifications or "inefficient" in classifications

def test_route_deviation_with_trips():
    r = requests.get(f"{BASE}/trips/route-deviation?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert "sample_trips" in data
    if data["total_trips_analysed"] > 0:
        assert len(data["sample_trips"]) > 0
        trip = data["sample_trips"][0]
        assert "deviation_index" in trip
        assert "classification" in trip
        assert trip["classification"] in ["efficient", "moderate", "inefficient"]

def test_route_deviation_invalid_dates_returns_400():
    r = requests.get(f"{BASE}/trips/route-deviation?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400


# ── UC03 — GET /trips/speed/zones ─────────────────────────────────────────────

def test_speed_zones_returns_200():
    r = requests.get(f"{BASE}/trips/speed/zones")
    assert r.status_code == 200

def test_speed_zones_has_real_data():
    r = requests.get(f"{BASE}/trips/speed/zones")
    data = r.json()
    assert data["total_results"] > 0
    assert len(data["zones"]) > 0

def test_speed_zones_classification_present():
    r = requests.get(f"{BASE}/trips/speed/zones?limit=5")
    for zone in r.json()["zones"]:
        assert zone["classification"] in ["slow", "normal", "fast"]
        assert zone["avg_speed_kmh"] > 0

def test_speed_zones_filter_by_period_peak():
    r = requests.get(f"{BASE}/trips/speed/zones?period=peak&limit=5")
    assert r.status_code == 200
    for zone in r.json()["zones"]:
        assert zone["time_period"] == "peak"

def test_speed_zones_filter_by_period_night():
    r = requests.get(f"{BASE}/trips/speed/zones?period=night&limit=5")
    assert r.status_code == 200

def test_speed_zones_invalid_period_returns_400():
    r = requests.get(f"{BASE}/trips/speed/zones?period=morning")
    assert r.status_code == 400

def test_speed_zones_invalid_dates_returns_400():
    r = requests.get(f"{BASE}/trips/speed/zones?start_date=2015-01-31&end_date=2015-01-01")
    assert r.status_code == 400


# ── UC22 — POST /trips ────────────────────────────────────────────────────────

def test_submit_trip_returns_201():
    r = requests.post(f"{BASE}/trips", json={
        "pickup_datetime":  "2015-01-10T08:30:00",
        "dropoff_datetime": "2015-01-10T08:55:00",
        "passenger_count": 2,
        "trip_distance_km": 5.63,
        "pickup_zone_id": 161,
        "pickup_zone_name": "Midtown Center",
        "dropoff_zone_id": 162,
        "dropoff_zone_name": "Midtown East",
        "fare_amount": 14.50,
        "tip_amount": 3.00,
        "payment_type": 1,
    })
    assert r.status_code == 201

def test_submit_trip_enriched_columns_computed():
    r = requests.post(f"{BASE}/trips", json={
        "pickup_datetime":  "2015-01-10T08:30:00",
        "dropoff_datetime": "2015-01-10T08:55:00",
        "passenger_count": 2,
        "trip_distance_km": 5.63,
        "pickup_zone_id": 161,
        "pickup_zone_name": "Midtown Center",
        "dropoff_zone_id": 162,
        "dropoff_zone_name": "Midtown East",
        "fare_amount": 14.50,
        "tip_amount": 3.00,
        "payment_type": 1,
    })
    assert r.status_code == 201
    data = r.json()
    assert "enriched" in data
    enriched = data["enriched"]
    assert enriched["time_class"] == "peak"
    assert enriched["deviation_class"] in ["efficient", "moderate", "inefficient"]
    assert enriched["speed_class"] in ["slow", "normal", "fast"]
    assert isinstance(enriched["suspicion_score"], int)
    assert isinstance(enriched["deviation_index"], float)
    assert isinstance(enriched["avg_speed_kmh"], float)

def test_submit_trip_appears_in_classification():
    """Viagem submetida aparece nos dados do UC01."""
    before = requests.get(f"{BASE}/trips/classification/time-of-day").json()["total_trips"]

    requests.post(f"{BASE}/trips", json={
        "pickup_datetime":  "2015-01-10T22:30:00",
        "dropoff_datetime": "2015-01-10T23:00:00",
        "passenger_count": 1,
        "trip_distance_km": 3.2,
        "pickup_zone_id": 161,
        "pickup_zone_name": "Midtown Center",
        "dropoff_zone_id": 162,
        "dropoff_zone_name": "Midtown East",
        "fare_amount": 12.0,
        "payment_type": 2,
    })

    after = requests.get(f"{BASE}/trips/classification/time-of-day").json()["total_trips"]
    assert after == before + 1

def test_submit_trip_dropoff_before_pickup_returns_422():
    r = requests.post(f"{BASE}/trips", json={
        "pickup_datetime":  "2015-01-10T09:00:00",
        "dropoff_datetime": "2015-01-10T08:00:00",
        "passenger_count": 1,
        "trip_distance_km": 3.0,
        "pickup_zone_id": 161,
        "pickup_zone_name": "Midtown Center",
        "dropoff_zone_id": 162,
        "dropoff_zone_name": "Midtown East",
        "fare_amount": 10.0,
        "payment_type": 1,
    })
    assert r.status_code == 422

def test_submit_trip_invalid_passenger_count_returns_422():
    r = requests.post(f"{BASE}/trips", json={
        "pickup_datetime":  "2015-01-10T08:30:00",
        "dropoff_datetime": "2015-01-10T08:55:00",
        "passenger_count": 10,
        "trip_distance_km": 3.0,
        "pickup_zone_id": 161,
        "pickup_zone_name": "Midtown Center",
        "dropoff_zone_id": 162,
        "dropoff_zone_name": "Midtown East",
        "fare_amount": 10.0,
        "payment_type": 1,
    })
    assert r.status_code == 422


# ── UC21 — DELETE /trips ──────────────────────────────────────────────────────

def test_bulk_delete_dry_run():
    r = requests.delete(f"{BASE}/trips/invalid/bulk?dry_run=true")
    assert r.status_code == 200
    data = r.json()
    assert data["dry_run"] is True
    assert "invalid_trips" in data

def test_delete_trip_not_found():
    r = requests.delete(f"{BASE}/trips/999999999")
    assert r.status_code == 404

def test_delete_trip_and_verify_removed():
    """Submete uma viagem, apaga-a e verifica que desapareceu."""
    post_r = requests.post(f"{BASE}/trips", json={
        "pickup_datetime":  "2015-01-10T08:30:00",
        "dropoff_datetime": "2015-01-10T08:55:00",
        "passenger_count": 1,
        "trip_distance_km": 2.0,
        "pickup_zone_id": 100,
        "pickup_zone_name": "Test Zone",
        "dropoff_zone_id": 101,
        "dropoff_zone_name": "Test Zone 2",
        "fare_amount": 8.0,
        "payment_type": 1,
    })
    assert post_r.status_code == 201
    trip_id = post_r.json()["trip_id"]

    delete_r = requests.delete(f"{BASE}/trips/{trip_id}")
    assert delete_r.status_code == 200
    assert delete_r.json()["deleted"] is True

    delete_again = requests.delete(f"{BASE}/trips/{trip_id}")
    assert delete_again.status_code == 404
