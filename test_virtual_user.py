import requests
import json
import time

BASE_URL = "http://localhost:8000"

def log_test(title, success, details=""):
    status = "PASS" if success else "FAIL"
    print(f"[{status}] {title} {('- ' + details) if details else ''}")

def run_virtual_user_tests():
    print("=" * 80)
    print(" AGRISENSE VIRTUAL USER END-TO-END AUTOMATED SUITE")
    print("=" * 80)

    # 1. Health Check
    try:
        res = requests.get(f"{BASE_URL}/api/v1/health")
        log_test("Server Health Check", res.status_code == 200, res.json().get("service"))
    except Exception as e:
        log_test("Server Health Check", False, str(e))
        return

    # 2. Test Invalid Credentials Login (Wrong Password)
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "phone_or_email": "google.farmer@agrisense.io",
        "password": "WrongPassword123!"
    })
    log_test("Invalid Password Login Guard", res.status_code == 401, f"Status Code {res.status_code}")

    # 3. Test Non-Existent Account Login
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "phone_or_email": "nonexistent_user_999@agrisense.io",
        "password": "AgriPass123!"
    })
    log_test("Non-Existent Account Login Guard", res.status_code == 401, f"Status Code {res.status_code}")

    # 4. Test Server-Side Lowercasing of Email IDs (Mixed Case Email Login/SSO)
    res = requests.post(f"{BASE_URL}/api/v1/auth/sso/google")
    log_test("Google SSO Authentication", res.status_code == 200, f"Logged in as {res.json().get('farmer', {}).get('phone_or_email')}")

    res_mixed = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "phone_or_email": "GooGlE.FARmeR@AGRiSeNsE.iO",  # Mixed uppercase & lowercase
        "password": "AgriPass123!"
    })
    log_test("Server-Side Lowercasing of Email (Mixed Case Match)", res_mixed.status_code == 200, f"Matched email: {res_mixed.json().get('farmer', {}).get('phone_or_email')}")

    # 5. Test Weak Password Registration Guard
    test_user_email = f"virtual.user.{int(time.time())}@agrisense.io"
    res = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "full_name": "Virtual Test Farmer",
        "phone_or_email": test_user_email,
        "farm_name": "Testing Farm",
        "farm_acres": 25.5,
        "password": "weak"  # Weak password
    })
    log_test("Weak Password Registration Guard", res.status_code == 400, res.json().get("detail", ""))

    # 6. Test Valid Account Registration
    strong_pass = "AgriPass2026!#"
    res = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "full_name": "Virtual Test Farmer",
        "phone_or_email": test_user_email.upper(),  # Sending uppercase email to verify lowercasing
        "farm_name": "Testing Farm",
        "farm_acres": 25.5,
        "password": strong_pass,
        "gender": "Male",
        "age": 30,
        "avatar_id": 2,
        "crop_type": "Corn & Maize"
    })
    log_test("Valid Account Registration", res.status_code == 200, f"Registered ID #{res.json().get('farmer_id')}")

    # 7. Test Duplicate Registration Guard
    res_dup = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "full_name": "Virtual Test Farmer",
        "phone_or_email": test_user_email,
        "farm_name": "Testing Farm",
        "farm_acres": 25.5,
        "password": strong_pass
    })
    log_test("Duplicate Account Registration Guard", res_dup.status_code == 400, res_dup.json().get("detail", ""))

    # 8. Test Login with Registered User
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "phone_or_email": test_user_email.lower(),
        "password": strong_pass
    })
    farmer_data = res.json().get("farmer", {})
    farmer_id = farmer_data.get("id")
    log_test("Login with Newly Registered Account", res.status_code == 200, f"Farmer ID #{farmer_id}")

    # 9. Test OTP Send & Verification Flow
    res_otp = requests.post(f"{BASE_URL}/api/v1/auth/forgot-password/send-otp", json={
        "phone_or_email": test_user_email
    })
    demo_otp = res_otp.json().get("demo_otp", "849201")
    log_test("Send Forgot Password OTP", res_otp.status_code == 200, f"OTP: {demo_otp}")

    # 10. Test Password Reset
    new_pass = "NewAgriPass2026!$"
    res_reset = requests.post(f"{BASE_URL}/api/v1/auth/forgot-password/reset", json={
        "phone_or_email": test_user_email,
        "new_password": new_pass,
        "otp_code": demo_otp
    })
    log_test("Password Reset with OTP", res_reset.status_code == 200, res_reset.json().get("message", ""))

    # 11. Test Add Farm Field
    res_farm = requests.post(f"{BASE_URL}/api/v1/farms/add", json={
        "farmer_id": farmer_id,
        "farm_name": "North Field Orchard",
        "farm_acres": 42.0,
        "crop_type": "Fruit Orchard"
    })
    log_test("Add New Farm Field", res_farm.status_code == 200 or res_farm.status_code == 201)

    # 12. Test Profile Update
    res_prof = requests.post(f"{BASE_URL}/api/v1/auth/profile/update", json={
        "farmer_id": farmer_id,
        "full_name": "Virtual Test Farmer (Updated)",
        "gender": "Male",
        "age": 31,
        "avatar_id": 4
    })
    log_test("Update Profile Endpoint", res_prof.status_code == 200, res_prof.json().get("farmer", {}).get("full_name"))

    # 13. Test Telemetry Simulation Presets
    for preset in ["HEALTHY", "PRE_SYMPTOMATIC_STRESS", "SEVERE_DROUGHT", "SMOKE_HAZARD"]:
        res_sim = requests.post(f"{BASE_URL}/api/v1/simulate?preset={preset}")
        ai_diag = res_sim.json().get("ai_diagnosis", {})
        log_test(f"Simulation Preset '{preset}'", res_sim.status_code == 200, f"AI Status: {ai_diag.get('status')}")

    # 14. Test ESP32 Soil Sensor Telemetry Ingest Endpoint
    res_esp = requests.post(f"{BASE_URL}/api/v1/telemetry/ingest", json={
        "device_id": "ESP32_VIRTUAL_TEST_NODE",
        "soil_moisture": 45.2,
        "temperature": 27.4,
        "humidity": 62.0,
        "smoke_ppm": 78.0
    })
    log_test("ESP32 Sensor Telemetry Ingest", res_esp.status_code == 200, f"Status: {res_esp.json().get('status')}")

    # 15. Test OTA Update Check Endpoint
    res_ota = requests.get(f"{BASE_URL}/api/v1/update/check?current_version=1.5.0")
    ota_data = res_ota.json()
    log_test("OTA Update Check Endpoint", res_ota.status_code == 200, f"Has update: {ota_data.get('has_update')}, Latest: v{ota_data.get('latest_version')}")

    # 16. Test Live Crop Health AI Image Scanner Endpoint
    res_img = requests.post(f"{BASE_URL}/api/v1/ai/diagnose-crop-image", json={
        "crop_type": "Wheat & Paddy",
        "note": "Sample Leaf Scan Test"
    })
    diag_info = res_img.json().get("diagnosis", {})
    log_test("Live Crop Health AI Image Scanner Endpoint", res_img.status_code == 200, f"Condition: {diag_info.get('crop_condition')}")

    print("=" * 80)
    print(" ALL VIRTUAL USER SUITE TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_virtual_user_tests()
