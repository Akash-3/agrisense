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

def test_direct_password_reset_success():
    # Insert test farmer with PBKDF2 hash
    from database import hash_password
    h = hash_password("OldPassword123!", salt="testsalt123")
    farmer_id = execute_db("INSERT INTO farmers (full_name, phone_or_email, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)", ("Reset Test", "reset_test_unit@test.com", h, "testsalt123", time.time()), return_lastrowid=True)
    
    # Direct password reset
    response = client.post("/api/v1/auth/forgot-password/reset", json={"phone_or_email": "reset_test_unit@test.com", "new_password": "NewStrongPassword123!"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_direct_password_reset_nonexistent_account():
    response = client.post("/api/v1/auth/forgot-password/reset", json={"phone_or_email": "nonexistent_999@test.com", "new_password": "NewStrongPassword123!"})
    assert response.status_code == 400


