import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
os.environ["JWT_SECRET_KEY"] = "test_secret_key"
import pytest
from pydantic import ValidationError
from routers.v2 import LawnmowerMissionRequest
import math

def test_mission_validation():
    # Valid
    valid_coords = [{'lat': 10.0, 'lng': 20.0}, {'lat': 10.1, 'lng': 20.0}, {'lat': 10.1, 'lng': 20.1}, {'lat': 10.0, 'lng': 20.1}]
    req = LawnmowerMissionRequest(boundary_coords=valid_coords)
    assert len(req.boundary_coords) == 4

    # lat > 90
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=[{'lat': 91.0, 'lng': 0.0}, {'lat': 0.0, 'lng': 0.0}, {'lat': 0.0, 'lng': 1.0}])

    # lat < -90
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=[{'lat': -91.0, 'lng': 0.0}, {'lat': 0.0, 'lng': 0.0}, {'lat': 0.0, 'lng': 1.0}])

    # lng > 180
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=[{'lat': 0.0, 'lng': 181.0}, {'lat': 0.0, 'lng': 0.0}, {'lat': 1.0, 'lng': 0.0}])

    # lng < -180
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=[{'lat': 0.0, 'lng': -181.0}, {'lat': 0.0, 'lng': 0.0}, {'lat': 1.0, 'lng': 0.0}])

    # NaN lat
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=[{'lat': float('nan'), 'lng': 0.0}, {'lat': 0.0, 'lng': 0.0}, {'lat': 1.0, 'lng': 0.0}])

    # NaN lng
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=[{'lat': 0.0, 'lng': float('nan')}, {'lat': 0.0, 'lng': 0.0}, {'lat': 1.0, 'lng': 0.0}])

    # Infinity
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=[{'lat': float('inf'), 'lng': 0.0}, {'lat': 0.0, 'lng': 0.0}, {'lat': 1.0, 'lng': 0.0}])

    # Missing lat
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=[{'lng': 0.0}, {'lat': 0.0, 'lng': 0.0}, {'lat': 1.0, 'lng': 0.0}])

    # Missing lng
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=[{'lat': 0.0}, {'lat': 0.0, 'lng': 0.0}, {'lat': 1.0, 'lng': 0.0}])

    # Malformed
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=[{'lat': 'string', 'lng': 0.0}, {'lat': 0.0, 'lng': 0.0}, {'lat': 1.0, 'lng': 0.0}])

    # Excessive polygon (limit is 200)
    with pytest.raises(ValidationError):
        excessive = [{'lat': 0.0, 'lng': 0.0} for _ in range(201)]
        LawnmowerMissionRequest(boundary_coords=excessive)

    # Existing spacing minimum (<1.0)
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=valid_coords, spacing_m=0.5)

    # Existing spacing maximum (>1000.0)
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=valid_coords, spacing_m=1001.0)

    # Existing altitude negative
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=valid_coords, altitude_m=-5.0)

    # Existing >0.5-degree boundary
    with pytest.raises(ValidationError):
        LawnmowerMissionRequest(boundary_coords=[{'lat': 0.0, 'lng': 0.0}, {'lat': 1.0, 'lng': 0.0}, {'lat': 0.0, 'lng': 1.0}])


# --------- REMEDIATION BATCH: Phase 9 — V2 API Auth + Phase 4 Actuator + Phase 11 Digital Twin ---------

import time

test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_mission_v.db'))
if os.path.exists(test_db_path):
    os.remove(test_db_path)
os.environ['DB_PATH'] = test_db_path
os.environ['DEVICE_API_KEY'] = 'test_mv_key'
os.environ['CORS_ALLOWED_ORIGINS'] = 'http://localhost:3000'

from fastapi.testclient import TestClient
from database import init_db, execute_db
init_db()

from main import app as mv_app
mv_client = TestClient(mv_app)

def mv_register_and_get_token(email="mv@test.com"):
    import time
    unique_email = f"{time.time()}_{email}"
    res = mv_client.post("/api/v1/auth/register", json={
        "full_name": "MV Farmer",
        "phone_or_email": unique_email,
        "password": "StrongPassword123!",
        "farm_name": "MV Farm",
        "farm_acres": 10.0,
        "crop_type": "Wheat",
        "gender": "Other",
        "age": 30
    })
    data = res.json()
    print("REGISTER DATA:", data)
    return data.get("session_token"), data.get("farm_id")

valid_spectral = [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]
valid_boundary = [
    {'lat': 10.0, 'lng': 20.0}, {'lat': 10.1, 'lng': 20.0},
    {'lat': 10.1, 'lng': 20.1}, {'lat': 10.0, 'lng': 20.1}
]

def test_phase9_predict_unauthenticated_rejected():
    """POST /api/v2/ai/predict must reject unauthenticated requests with 401/403."""
    res = mv_client.post("/api/v2/ai/predict", json={
        "spectral": valid_spectral, "temperature": 25.0,
        "humidity": 60.0, "soil_moisture": 45.0, "smoke_ppm": 80.0
    })
    assert res.status_code in (401, 403)

def test_phase9_predict_authenticated_succeeds():
    """POST /api/v2/ai/predict succeeds for an authenticated user."""
    token, _ = mv_register_and_get_token("mv_predict@test.com")
    res = mv_client.post("/api/v2/ai/predict", headers={"Authorization": f"Bearer {token}"}, json={
        "spectral": valid_spectral, "temperature": 25.0,
        "humidity": 60.0, "soil_moisture": 45.0, "smoke_ppm": 80.0
    })
    assert res.status_code == 200

def test_phase9_uav_mission_unauthenticated_rejected():
    """POST /api/v2/uav/mission/generate must reject unauthenticated requests."""
    res = mv_client.post("/api/v2/uav/mission/generate", json={"boundary_coords": valid_boundary})
    assert res.status_code in (401, 403)

def test_phase9_uav_mission_authenticated_succeeds():
    """POST /api/v2/uav/mission/generate succeeds for an authenticated user."""
    token, _ = mv_register_and_get_token("mv_uav@test.com")
    res = mv_client.post("/api/v2/uav/mission/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={"boundary_coords": valid_boundary})
    assert res.status_code == 200

def test_phase9_hotspots_unauthenticated_rejected():
    """POST /api/v2/spatial/hotspots must reject unauthenticated requests."""
    res = mv_client.post("/api/v2/spatial/hotspots", json=[])
    assert res.status_code in (401, 403)

def test_phase9_hotspots_simulation_unauthenticated_rejected():
    """GET /api/v2/spatial/hotspots/simulation must reject unauthenticated requests."""
    res = mv_client.get("/api/v2/spatial/hotspots/simulation")
    assert res.status_code in (401, 403)

def test_phase10_image_endpoint_unauthenticated_rejected():
    """POST /api/v1/ai/diagnose-crop-image must reject unauthenticated requests."""
    res = mv_client.post("/api/v1/ai/diagnose-crop-image", json={"image_base64": ""})
    assert res.status_code in (401, 403)

def test_phase10_image_size_validation_preserved():
    """Existing 413 size check still works (auth aside for this test we use a valid token)."""
    token, _ = mv_register_and_get_token("mv_img@test.com")
    huge_str = 'A' * (8 * 1024 * 1024)
    res = mv_client.post("/api/v1/ai/diagnose-crop-image",
        headers={"Authorization": f"Bearer {token}"},
        json={"image_base64": huge_str})
    assert res.status_code == 413

def test_phase11_digital_twin_scenario_isolation():
    """User A setting scenario A must not affect User B seeing scenario B."""
    token_a, _ = mv_register_and_get_token("dt_user_a@test.com")
    token_b, _ = mv_register_and_get_token("dt_user_b@test.com")

    # User A sets WATER_STRESS_EPISODE
    res_a = mv_client.post("/api/v2/simulation/digital-twin/set-scenario",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"scenario_name": "WATER_STRESS_EPISODE"})
    assert res_a.status_code == 200
    assert res_a.json()["digital_twin"]["active_scenario"] == "WATER_STRESS_EPISODE"

    # User B sets FUNGAL_DISEASE_OUTBREAK
    res_b = mv_client.post("/api/v2/simulation/digital-twin/set-scenario",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"scenario_name": "FUNGAL_DISEASE_OUTBREAK"})
    assert res_b.status_code == 200
    assert res_b.json()["digital_twin"]["active_scenario"] == "FUNGAL_DISEASE_OUTBREAK"

    # User A's telemetry must still reflect WATER_STRESS_EPISODE
    tel_a = mv_client.get("/api/v2/simulation/digital-twin/telemetry",
        headers={"Authorization": f"Bearer {token_a}"})
    assert tel_a.status_code == 200
    assert tel_a.json()["simulated_telemetry"]["scenario"] == "WATER_STRESS_EPISODE"

    # User B's telemetry must still reflect FUNGAL_DISEASE_OUTBREAK
    tel_b = mv_client.get("/api/v2/simulation/digital-twin/telemetry",
        headers={"Authorization": f"Bearer {token_b}"})
    assert tel_b.status_code == 200
    assert tel_b.json()["simulated_telemetry"]["scenario"] == "FUNGAL_DISEASE_OUTBREAK"
