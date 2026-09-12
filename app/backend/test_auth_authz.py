import sys
import os
import time
import pytest
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Set a completely isolated database for testing BEFORE importing main
test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_isolated_auth.db'))
if os.path.exists(test_db_path):
    os.remove(test_db_path)
os.environ["DB_PATH"] = test_db_path

from fastapi.testclient import TestClient
from database import execute_db, create_session_token, init_db

# Initialize the new isolated test DB
init_db()

from main import app
client = TestClient(app)

def test_protected_endpoint_without_auth():
    response = client.post("/api/v1/auth/profile/update", json={"full_name": "Test"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_protected_endpoint_with_invalid_token():
    response = client.post("/api/v1/auth/profile/update", headers={"Authorization": "Bearer invalid_token"}, json={"full_name": "Test"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired session token"

def test_valid_token_succeeds():
    farmer_id = execute_db("INSERT INTO farmers (full_name, phone_or_email, password_hash, created_at) VALUES (?, ?, ?, ?)", ("Test", "test29@test.com", "hash", time.time()), return_lastrowid=True)
    token = create_session_token(farmer_id)
    response = client.post("/api/v1/auth/profile/update", headers={"Authorization": f"Bearer {token}"}, json={"full_name": "Test Valid"})
    assert response.status_code == 200

def test_valid_token_another_farmer_id_ignored():
    farmer_id = execute_db("INSERT INTO farmers (full_name, phone_or_email, password_hash, created_at) VALUES (?, ?, ?, ?)", ("Test A", "testA@test.com", "hash", time.time()), return_lastrowid=True)
    token = create_session_token(farmer_id)
    response = client.post("/api/v1/auth/profile/update", headers={"Authorization": f"Bearer {token}"}, json={"full_name": "Test Tampered", "farmer_id": 99999})
    assert response.status_code == 200

def test_logout_invalidates_session():
    farmer_id = execute_db("INSERT INTO farmers (full_name, phone_or_email, password_hash, created_at) VALUES (?, ?, ?, ?)", ("Test2", "test30@test.com", "hash", time.time()), return_lastrowid=True)
    token = create_session_token(farmer_id)
    response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    response = client.post("/api/v1/auth/profile/update", headers={"Authorization": f"Bearer {token}"}, json={"full_name": "Test Valid"})
    assert response.status_code == 401

def test_registration_missing_otp():
    response = client.post("/api/v1/auth/register", json={"full_name": "Test", "phone_or_email": "x@x.com", "password": "pass", "otp_code": ""})
    assert response.status_code in [400, 422]
