import sys
import os
import time
import pytest
import sqlite3
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_isolated_zones.db'))
if os.path.exists(test_db_path):
    os.remove(test_db_path)
os.environ["DB_PATH"] = test_db_path
os.environ["JWT_SECRET_KEY"] = "test_secret_key"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000"

from fastapi.testclient import TestClient
from database import execute_db, create_session_token, init_db

init_db()

from main import app
client = TestClient(app)

def create_test_user_and_farm(email: str):
    farmer_id = execute_db(
        "INSERT INTO farmers (full_name, phone_or_email, password_hash, created_at) VALUES (?, ?, ?, ?)", 
        ("Test User", email, "hash", time.time()), return_lastrowid=True
    )
    token = create_session_token(farmer_id)
    farm_id = execute_db(
        "INSERT INTO farms (farmer_id, farm_name, farm_acres, created_at) VALUES (?, ?, ?, ?)",
        (farmer_id, "Test Farm", 10.0, time.time()), return_lastrowid=True
    )
    return farmer_id, farm_id, token

def test_create_zone_in_own_farm():
    farmer_id, farm_id, token = create_test_user_and_farm("zone1@test.com")
    response = client.post(
        f"/api/v1/farms/{farm_id}/zones",
        headers={"Authorization": f"Bearer {token}"},
        json={"zone_name": "Zone A", "acres": 5.0, "polygon_coords": "[[0,0],[0,1],[1,1]]"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "zone_id" in data

def test_list_own_zones():
    farmer_id, farm_id, token = create_test_user_and_farm("zone2@test.com")
    execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone Z", 2.0, time.time()), commit=True)
    response = client.get(
        f"/api/v1/farms/{farm_id}/zones",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()["zones"]) == 1
    assert response.json()["zones"][0]["zone_name"] == "Zone Z"

def test_update_own_zone():
    farmer_id, farm_id, token = create_test_user_and_farm("zone3@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone Old", 2.0, time.time()), return_lastrowid=True, commit=True)
    response = client.put(
        f"/api/v1/zones/{zone_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"zone_name": "Zone New"}
    )
    assert response.status_code == 200

def test_cannot_access_another_farmers_zones():
    # User 1
    f1, farm1, t1 = create_test_user_and_farm("u1@test.com")
    # User 2
    f2, farm2, t2 = create_test_user_and_farm("u2@test.com")
    
    # User 1 tries to list User 2's farm
    response = client.get(f"/api/v1/farms/{farm2}/zones", headers={"Authorization": f"Bearer {t1}"})
    assert response.status_code == 403

def test_invalid_polygon_rejected():
    farmer_id, farm_id, token = create_test_user_and_farm("zone4@test.com")
    response = client.post(
        f"/api/v1/farms/{farm_id}/zones",
        headers={"Authorization": f"Bearer {token}"},
        json={"zone_name": "Zone Bad", "acres": 5.0, "polygon_coords": "not-a-json"}
    )
    assert response.status_code == 422

def test_polygon_fewer_than_3_points_rejected():
    farmer_id, farm_id, token = create_test_user_and_farm("zone5@test.com")
    response = client.post(
        f"/api/v1/farms/{farm_id}/zones",
        headers={"Authorization": f"Bearer {token}"},
        json={"zone_name": "Zone Bad", "acres": 5.0, "polygon_coords": "[[0,0], [1,1]]"}
    )
    assert response.status_code == 422

def test_non_positive_acres_rejected():
    farmer_id, farm_id, token = create_test_user_and_farm("zone6@test.com")
    response = client.post(
        f"/api/v1/farms/{farm_id}/zones",
        headers={"Authorization": f"Bearer {token}"},
        json={"zone_name": "Zone Bad", "acres": -5.0}
    )
    assert response.status_code == 422

def test_create_crop_in_own_zone():
    farmer_id, farm_id, token = create_test_user_and_farm("crop1@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone", 2.0, time.time()), return_lastrowid=True, commit=True)
    response = client.post(
        f"/api/v1/zones/{zone_id}/crops",
        headers={"Authorization": f"Bearer {token}"},
        json={"crop_name": "Wheat"}
    )
    assert response.status_code == 200
    assert "crop_id" in response.json()

def test_list_crops():
    farmer_id, farm_id, token = create_test_user_and_farm("crop2@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone", 2.0, time.time()), return_lastrowid=True, commit=True)
    execute_db("INSERT INTO crops (zone_id, crop_name, status, planted_date, created_at) VALUES (?, ?, ?, ?, ?)", (zone_id, "Rice", "PLANTED", time.time(), time.time()), commit=True)
    
    response = client.get(f"/api/v1/zones/{zone_id}/crops", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()["crops"]) == 1

def test_update_own_crop():
    farmer_id, farm_id, token = create_test_user_and_farm("crop3@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone", 2.0, time.time()), return_lastrowid=True, commit=True)
    crop_id = execute_db("INSERT INTO crops (zone_id, crop_name, status, planted_date, created_at) VALUES (?, ?, ?, ?, ?)", (zone_id, "Rice", "PLANTED", time.time(), time.time()), return_lastrowid=True, commit=True)
    
    response = client.put(f"/api/v1/crops/{crop_id}", headers={"Authorization": f"Bearer {token}"}, json={"crop_name": "Soybean"})
    assert response.status_code == 200

def test_cannot_access_another_farmers_zone_or_crop():
    f1, farm1, t1 = create_test_user_and_farm("cu1@test.com")
    f2, farm2, t2 = create_test_user_and_farm("cu2@test.com")
    zone1 = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm1, "Zone 1", 2.0, time.time()), return_lastrowid=True, commit=True)
    crop1 = execute_db("INSERT INTO crops (zone_id, crop_name, status, planted_date, created_at) VALUES (?, ?, ?, ?, ?)", (zone1, "Rice", "PLANTED", time.time(), time.time()), return_lastrowid=True, commit=True)
    
    res1 = client.post(f"/api/v1/zones/{zone1}/crops", headers={"Authorization": f"Bearer {t2}"}, json={"crop_name": "Wheat"})
    assert res1.status_code == 403
    res2 = client.put(f"/api/v1/crops/{crop1}", headers={"Authorization": f"Bearer {t2}"}, json={"crop_name": "Wheat"})
    assert res2.status_code == 403

def test_empty_crop_name_rejected():
    farmer_id, farm_id, token = create_test_user_and_farm("crop4@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone", 2.0, time.time()), return_lastrowid=True, commit=True)
    response = client.post(
        f"/api/v1/zones/{zone_id}/crops",
        headers={"Authorization": f"Bearer {token}"},
        json={"crop_name": ""}
    )
    assert response.status_code == 422

def test_second_planted_crop_rejected():
    farmer_id, farm_id, token = create_test_user_and_farm("crop5@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone", 2.0, time.time()), return_lastrowid=True, commit=True)
    
    # 1st crop
    res1 = client.post(f"/api/v1/zones/{zone_id}/crops", headers={"Authorization": f"Bearer {token}"}, json={"crop_name": "Wheat", "status": "PLANTED"})
    assert res1.status_code == 200
    
    # 2nd crop
    res2 = client.post(f"/api/v1/zones/{zone_id}/crops", headers={"Authorization": f"Bearer {token}"}, json={"crop_name": "Rice", "status": "PLANTED"})
    assert res2.status_code == 409

def test_historical_crop_can_coexist():
    farmer_id, farm_id, token = create_test_user_and_farm("crop6@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone", 2.0, time.time()), return_lastrowid=True, commit=True)

    
    # 1st crop harvested
    res1 = client.post(f"/api/v1/zones/{zone_id}/crops", headers={"Authorization": f"Bearer {token}"}, json={"crop_name": "Wheat", "status": "HARVESTED"})
    assert res1.status_code == 200
    
    # 2nd crop planted
    res2 = client.post(f"/api/v1/zones/{zone_id}/crops", headers={"Authorization": f"Bearer {token}"}, json={"crop_name": "Rice", "status": "PLANTED"})
    assert res2.status_code == 200

def test_empty_polygon_rejected_on_create():
    farmer_id, farm_id, token = create_test_user_and_farm("zone7@test.com")
    response = client.post(
        f"/api/v1/farms/{farm_id}/zones",
        headers={"Authorization": f"Bearer {token}"},
        json={"zone_name": "Zone Bad", "acres": 5.0, "polygon_coords": "[]"}
    )
    assert response.status_code == 422

def test_empty_polygon_rejected_on_update():
    farmer_id, farm_id, token = create_test_user_and_farm("zone8@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone Z", 2.0, time.time()), return_lastrowid=True, commit=True)
    response = client.put(
        f"/api/v1/zones/{zone_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"polygon_coords": "[]"}
    )
    assert response.status_code == 422

def test_fewer_than_3_polygon_points_rejected_on_update():
    farmer_id, farm_id, token = create_test_user_and_farm("zone9@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone Z", 2.0, time.time()), return_lastrowid=True, commit=True)
    response = client.put(
        f"/api/v1/zones/{zone_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"polygon_coords": "[[0,0], [1,1]]"}
    )
    assert response.status_code == 422

def test_zero_or_negative_acres_rejected_on_update():
    farmer_id, farm_id, token = create_test_user_and_farm("zone10@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone Z", 2.0, time.time()), return_lastrowid=True, commit=True)
    response = client.put(
        f"/api/v1/zones/{zone_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"acres": 0}
    )
    assert response.status_code == 422
    response2 = client.put(
        f"/api/v1/zones/{zone_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"acres": -1.5}
    )
    assert response2.status_code == 422

def test_empty_zone_name_rejected_on_update():
    farmer_id, farm_id, token = create_test_user_and_farm("zone11@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone Z", 2.0, time.time()), return_lastrowid=True, commit=True)
    response = client.put(
        f"/api/v1/zones/{zone_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"zone_name": ""}
    )
    assert response.status_code == 422

def test_invalid_crop_status_rejected_on_update():
    farmer_id, farm_id, token = create_test_user_and_farm("crop7@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone", 2.0, time.time()), return_lastrowid=True, commit=True)
    crop_id = execute_db("INSERT INTO crops (zone_id, crop_name, status, planted_date, created_at) VALUES (?, ?, ?, ?, ?)", (zone_id, "Rice", "PLANTED", time.time(), time.time()), return_lastrowid=True, commit=True)
    response = client.put(
        f"/api/v1/crops/{crop_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "UNKNOWN"}
    )
    assert response.status_code == 422



def test_assign_device_to_own_zone():
    farmer_id, farm_id, token = create_test_user_and_farm("device1@test.com")
    zone_id = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone D1", 2.0, time.time()), return_lastrowid=True, commit=True)
    res = client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token}"}, json={"device_id": "DEV_001", "zone_id": zone_id})
    assert res.status_code == 200
    db_res = execute_db("SELECT zone_id FROM devices WHERE device_id = 'DEV_001'", fetchone=True)
    assert db_res[0] == zone_id

def test_cannot_assign_device_to_others_zone():
    f1, farm1, t1 = create_test_user_and_farm("device2@test.com")
    f2, farm2, t2 = create_test_user_and_farm("device3@test.com")
    zone1 = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm1, "Zone D2", 2.0, time.time()), return_lastrowid=True, commit=True)
    res = client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {t2}"}, json={"device_id": "DEV_002", "zone_id": zone1})
    assert res.status_code == 403

def test_device_reassignment():
    farmer_id, farm_id, token = create_test_user_and_farm("device4@test.com")
    zone1 = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone A", 2.0, time.time()), return_lastrowid=True, commit=True)
    zone2 = execute_db("INSERT INTO zones (farm_id, zone_name, acres, created_at) VALUES (?, ?, ?, ?)", (farm_id, "Zone B", 2.0, time.time()), return_lastrowid=True, commit=True)
    client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token}"}, json={"device_id": "DEV_003", "zone_id": zone1})
    res = client.post("/api/v1/devices/assign", headers={"Authorization": f"Bearer {token}"}, json={"device_id": "DEV_003", "zone_id": zone2})
    assert res.status_code == 200
    db_res = execute_db("SELECT zone_id FROM devices WHERE device_id = 'DEV_003'", fetchall=True)
    assert len(db_res) == 1
    assert db_res[0][0] == zone2

