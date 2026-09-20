import sys
import os
import time
import pytest
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Set a completely isolated database for testing BEFORE importing main
test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_device_mgmt.db'))
if os.path.exists(test_db_path):
    os.remove(test_db_path)
os.environ["DB_PATH"] = test_db_path
os.environ["JWT_SECRET_KEY"] = "test_secret_key"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000"

from fastapi.testclient import TestClient
from database import execute_db, assign_device, get_devices_for_farm, get_device_by_device_id, init_db

# Initialize the new isolated test DB
init_db()

from main import app
client = TestClient(app)

def create_test_user_and_farm(email):
    # Register user
    res = client.post("/api/v1/auth/register", json={
        "full_name": "Test Farmer",
        "phone_or_email": email,
        "password": "StrongPassword123!",
        "farm_name": "Test Farm",
        "farm_acres": 10.0,
        "crop_type": "Wheat",
        "gender": "Other",
        "age": 30
    })
    data = res.json()
    farmer_id = data["farmer_id"]
    farm_id = data["farm_id"]
    token = data["session_token"]
    return farmer_id, farm_id, token

def create_test_zone(farm_id):
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, polygon_coords, created_at) VALUES (?, ?, ?, ?, ?)", 
        (farm_id, "Test Zone", 5.0, "[]", time.time()), return_lastrowid=True, commit=True)
    return zone_id

def test_assign_device_to_own_zone():
    # 1. authenticated user can assign a device to their own zone
    _, farm_id, token = create_test_user_and_farm("assign1@test.com")
    zone_id = create_test_zone(farm_id)
    
    res = client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token}"}, json={
        "device_id": "TEST_DEVICE_01",
        "zone_id": zone_id
    })
    assert res.status_code == 200
    
    # verify
    d = get_device_by_device_id("TEST_DEVICE_01")
    assert d is not None
    assert d["zone_id"] == zone_id

def test_cannot_assign_device_to_others_zone():
    # 2. authenticated user cannot assign a device to another user's zone
    _, farm_id1, _ = create_test_user_and_farm("assign_other1@test.com")
    zone_id1 = create_test_zone(farm_id1)
    
    _, _, token2 = create_test_user_and_farm("assign_other2@test.com")
    
    res = client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token2}"}, json={
        "device_id": "TEST_DEVICE_02",
        "zone_id": zone_id1
    })
    assert res.status_code == 403

def test_existing_device_reassignment():
    # 3. existing device reassignment respects ownership
    _, farm_id1, token1 = create_test_user_and_farm("reassign1@test.com")
    zone_id1 = create_test_zone(farm_id1)
    zone_id2 = create_test_zone(farm_id1)
    
    # Assign to zone 1
    client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token1}"}, json={
        "device_id": "TEST_DEVICE_03",
        "zone_id": zone_id1
    })
    
    # Reassign to zone 2
    res = client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token1}"}, json={
        "device_id": "TEST_DEVICE_03",
        "zone_id": zone_id2
    })
    assert res.status_code == 200
    
    d = get_device_by_device_id("TEST_DEVICE_03")
    assert d["zone_id"] == zone_id2

def test_duplicate_device_id_behavior():
    # 4. duplicate device ID behavior (reassignment)
    # The requirement is that it just updates the zone_id
    _, farm_id1, token1 = create_test_user_and_farm("dup1@test.com")
    zone_id1 = create_test_zone(farm_id1)
    
    res1 = client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token1}"}, json={
        "device_id": "DUP_DEVICE",
        "zone_id": zone_id1
    })
    assert res1.status_code == 200
    
    res2 = client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token1}"}, json={
        "device_id": "DUP_DEVICE",
        "zone_id": zone_id1
    })
    assert res2.status_code == 200

def test_list_devices_own_farm():
    # 5. listing devices for own farm/zone
    _, farm_id, token = create_test_user_and_farm("list1@test.com")
    zone_id = create_test_zone(farm_id)
    
    client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token}"}, json={
        "device_id": "LIST_DEVICE_1",
        "zone_id": zone_id
    })
    
    res = client.get(f"/api/v1/farms/{farm_id}/devices", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["devices"]) == 1
    assert data["devices"][0]["device_id"] == "LIST_DEVICE_1"

def test_unauthorized_device_listing():
    # 6. unauthorized device listing
    _, farm_id1, _ = create_test_user_and_farm("list_unauth1@test.com")
    _, _, token2 = create_test_user_and_farm("list_unauth2@test.com")
    
    res = client.get(f"/api/v1/farms/{farm_id1}/devices", headers={"Authorization": f"Bearer {token2}"})
    assert res.status_code == 403

def test_empty_device_list():
    # 7. empty device list works correctly
    _, farm_id, token = create_test_user_and_farm("empty_list@test.com")
    
    res = client.get(f"/api/v1/farms/{farm_id}/devices", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["devices"]) == 0

def test_no_fake_device_created():
    # 8. no fake device is created
    # Check that after creating a user, no ESP32_MULTI_NODE_01 exists automatically
    # Or any other devices
    create_test_user_and_farm("nofake@test.com")
    # Using raw SQL to ensure no devices are tied unless explicitly assigned
    res = execute_db("SELECT COUNT(*) FROM devices", fetchone=True)
    # The count might be non-zero from previous tests in the run, but we just verify ESP32_MULTI_NODE_01 wasn't created
    d = get_device_by_device_id("ESP32_MULTI_NODE_01")
    assert d is None


# --------- REMEDIATION BATCH: Phase 3 — Device Reassignment IDOR ---------

def test_phase3_user_b_cannot_steal_user_a_device():
    """User B must NOT be able to move User A's existing device to User B's zone."""
    # User A
    _, farm_a, token_a = create_test_user_and_farm("idor_a@test.com")
    zone_a = create_test_zone(farm_a)

    # Assign device to User A's zone
    res = client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token_a}"}, json={
        "device_id": "IDOR_DEVICE_01",
        "zone_id": zone_a
    })
    assert res.status_code == 200

    # User B
    _, farm_b, token_b = create_test_user_and_farm("idor_b@test.com")
    zone_b = create_test_zone(farm_b)

    # User B attempts to move User A's device into User B's zone
    res2 = client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token_b}"}, json={
        "device_id": "IDOR_DEVICE_01",
        "zone_id": zone_b
    })
    assert res2.status_code == 403, f"Expected 403, got {res2.status_code}: {res2.text}"

    # Verify device is still in User A's zone
    d = get_device_by_device_id("IDOR_DEVICE_01")
    assert d["zone_id"] == zone_a, "Device zone must remain User A's zone"

def test_phase3_user_a_can_reassign_own_device_between_own_zones():
    """User A can reassign their own device between their own zones."""
    _, farm_a, token_a = create_test_user_and_farm("idor_own_a@test.com")
    zone_a1 = create_test_zone(farm_a)
    zone_a2 = create_test_zone(farm_a)

    # Assign to zone_a1
    client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token_a}"}, json={
        "device_id": "IDOR_DEVICE_02",
        "zone_id": zone_a1
    })
    # Reassign to zone_a2
    res = client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token_a}"}, json={
        "device_id": "IDOR_DEVICE_02",
        "zone_id": zone_a2
    })
    assert res.status_code == 200
    d = get_device_by_device_id("IDOR_DEVICE_02")
    assert d["zone_id"] == zone_a2

