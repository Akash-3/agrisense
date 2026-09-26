import os
import sys
import time
import sqlite3
import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("APP_URL", "http://localhost:8000")
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "app", "backend", "agrisense_farmer.db"))

def test_mandatory_suite_a_through_f():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ----------------------------------------------------
        # 1. MAP RESPONSIVE VIEWPORT TESTING (360x800, 390x844, 768x1024, 1440x900)
        # ----------------------------------------------------
        viewports = [
            {"width": 360, "height": 800, "name": "Mobile Small"},
            {"width": 390, "height": 844, "name": "Mobile Standard"},
            {"width": 768, "height": 1024, "name": "Tablet"},
            {"width": 1440, "height": 900, "name": "Desktop"}
        ]
        
        for vp in viewports:
            page = browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
            page.goto(BASE_URL, wait_until="domcontentloaded")
            time.sleep(0.5)
            
            reg_tab = page.query_selector("button:has-text('Register')")
            if reg_tab:
                reg_tab.click()
                time.sleep(0.3)
            
            page.fill("#regName", f"Tester {vp['name']}")
            page.fill("#regEmail", f"vp_{int(time.time())}_{vp['width']}@agrisense.test")
            page.fill("#regPass", "SecurePass123!")
            
            page.click("button:has-text('Next: Configure Farm')")
            time.sleep(0.8)
            
            map_box = page.query_selector("#wizardMap")
            assert map_box is not None, f"Map element missing on {vp['name']}"
            time.sleep(0.5)
            dims = page.evaluate("() => { const el = document.getElementById('wizardMap'); return { width: el.offsetWidth, height: el.offsetHeight }; }")
            assert dims is not None and dims["width"] > 0 and dims["height"] > 0, f"Map height/width collapsed on {vp['name']}: {dims}"
            print(f"[OK] Viewport {vp['name']} ({vp['width']}x{vp['height']}): Map rendered with layout dimensions {dims['width']}x{dims['height']}px")
            page.close()

        # ----------------------------------------------------
        # TEST C & A: REGISTRATION AND EMAIL LOGIN
        # ----------------------------------------------------
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        console_errors = []
        failed_requests = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("requestfailed", lambda req: failed_requests.append(req.url))

        page.goto(BASE_URL, wait_until="domcontentloaded")
        
        test_email = f"farmer_email_{int(time.time())}@agrisense.test"
        test_pass = "EmailPassword123!"
        
        # Open Register Tab
        page.click("button:has-text('Register')")
        time.sleep(0.3)
        page.fill("#regName", "Email Test Farmer")
        page.fill("#regEmail", test_email)
        page.select_option("#regGender", "Male")
        page.fill("#regAge", "32")
        page.fill("#regPass", test_pass)
        
        page.click("button:has-text('Next: Configure Farm')")
        time.sleep(0.8)
        
        map_box = page.query_selector("#wizardMap")
        box = map_box.bounding_box()
        page.mouse.click(box["x"] + 100, box["y"] + 100)
        time.sleep(0.2)
        page.mouse.click(box["x"] + 140, box["y"] + 120)
        time.sleep(0.2)
        page.mouse.click(box["x"] + 110, box["y"] + 150)
        time.sleep(0.5)
        
        acreage_text = page.text_content("#wizardAcreageDisplay")
        assert "0.00" not in acreage_text, "Acreage must update after placing 3 boundary points"
        
        page.click("button:has-text('Complete Setup')")
        page.wait_for_selector("#mainAppScreen:not(.hidden)", timeout=10000)
        print("[OK] TEST C — REGISTRATION: Account created via website UI and logged in!")

        # Logout
        page.evaluate("window.UI.logout()")
        page.wait_for_selector("#authScreen:not(.hidden)", timeout=5000)
        
        # EMAIL LOGIN (TEST A)
        page.fill("#loginIdInput", test_email)
        page.fill("#loginPassInput", test_pass)
        page.click("button:has-text('Sign In')")
        page.wait_for_selector("#mainAppScreen:not(.hidden)", timeout=10000)
        
        user_state = page.evaluate("window.AgriState.currentUser")
        assert user_state["isAuthenticated"] is True
        assert user_state["email"] == test_email
        print("[OK] TEST A — EMAIL LOGIN: Login succeeded, dashboard loaded, session established!")

        page.evaluate("window.UI.logout()")
        page.wait_for_selector("#authScreen:not(.hidden)", timeout=5000)

        # ----------------------------------------------------
        # TEST B: PHONE LOGIN
        # ----------------------------------------------------
        test_phone = f"+1555{int(time.time()) % 10000000:07d}"
        phone_reg_email = f"phone_acc_{int(time.time())}@agrisense.test"
        test_phone_pass = "PhonePassword123!"
        
        page.click("button:has-text('Register')")
        time.sleep(0.3)
        page.fill("#regName", "Phone Farmer")
        page.fill("#regEmail", test_phone)
        page.fill("#regPass", test_phone_pass)
        page.click("button:has-text('Next: Configure Farm')")
        time.sleep(0.8)
        page.click("button:has-text('Complete Setup')")
        page.wait_for_selector("#mainAppScreen:not(.hidden)", timeout=10000)
        
        page.evaluate("window.UI.logout()")
        page.wait_for_selector("#authScreen:not(.hidden)", timeout=5000)
        
        # Phone Login
        page.fill("#loginIdInput", test_phone)
        page.fill("#loginPassInput", test_phone_pass)
        page.click("button:has-text('Sign In')")
        page.wait_for_selector("#mainAppScreen:not(.hidden)", timeout=10000)
        
        phone_user_state = page.evaluate("window.AgriState.currentUser")
        assert phone_user_state["isAuthenticated"] is True
        print("[OK] TEST B — PHONE LOGIN: Phone authentication succeeded without 403!")

        page.evaluate("window.UI.logout()")
        page.wait_for_selector("#authScreen:not(.hidden)", timeout=5000)

# ----------------------------------------------------
        # TEST D: DIRECT FORGOT PASSWORD RESET (NO OTP)
        # ----------------------------------------------------
        reset_email = f"reset_target_{int(time.time())}@agrisense.test"
        old_pass = "OldPassword123!"
        new_pass = "NewPassword123!"
        
        # Create user account for reset test
        page.click("button:has-text('Register')")
        time.sleep(0.3)
        page.fill("#regName", "Reset Farmer")
        page.fill("#regEmail", reset_email)
        page.fill("#regPass", old_pass)
        page.click("button:has-text('Next: Configure Farm')")
        time.sleep(0.8)
        page.click("button:has-text('Complete Setup')")
        page.wait_for_selector("#mainAppScreen:not(.hidden)", timeout=10000)
        
        page.evaluate("window.UI.logout()")
        page.wait_for_selector("#authScreen:not(.hidden)", timeout=5000)
        
        # Click Forgot Password
        page.click("a:has-text('Forgot Password?')")
        time.sleep(0.5)
        
        # Fill Direct Password Reset Form
        page.fill("#resetIdInput", reset_email)
        page.fill("#resetNewPasswordInput", new_pass)
        page.fill("#resetConfirmPasswordInput", new_pass)
        page.click("button:has-text('Update & Reset Password')")
        time.sleep(1.5)
        
        # Login with NEW password
        page.fill("#loginIdInput", reset_email)
        page.fill("#loginPassInput", new_pass)
        page.click("button:has-text('Sign In')")
        page.wait_for_selector("#mainAppScreen:not(.hidden)", timeout=10000)
        
        reset_user_state = page.evaluate("window.AgriState.currentUser")
        assert reset_user_state["isAuthenticated"] is True
        print("[OK] TEST D — DIRECT FORGOT PASSWORD RESET: Password updated and login with new password PASSED 100%!")

        page.evaluate("window.UI.logout()")
        page.wait_for_selector("#authScreen:not(.hidden)", timeout=5000)

        # ----------------------------------------------------
        # TEST E: INVALID CREDENTIALS & SECURITY
        # ----------------------------------------------------
        # 1. Correct email + wrong password -> rejected
        page.fill("#loginIdInput", test_email)
        page.fill("#loginPassInput", "WrongPassword999!")
        page.click("button:has-text('Sign In')")
        time.sleep(1)
        toast_msg = page.text_content("#toastMessage")
        assert "Invalid" in toast_msg or "error" in toast_msg.lower() or "failed" in toast_msg.lower()
        print("[OK] TEST E — INVALID CREDENTIALS: Wrong password properly rejected!")

        # ----------------------------------------------------
        # TEST F: DIRECT PASSWORD RESET SECURITY (NONEXISTENT ACCOUNT REJECTED)
        # ----------------------------------------------------
        page.click("a:has-text('Forgot Password?')")
        time.sleep(0.5)
        nonexistent_email = f"unknown_{int(time.time())}@agrisense.test"
        page.fill("#resetIdInput", nonexistent_email)
        page.fill("#resetNewPasswordInput", "ValidPass123!")
        page.fill("#resetConfirmPasswordInput", "ValidPass123!")
        page.click("button:has-text('Update & Reset Password')")
        page.wait_for_function("() => { const el = document.getElementById('toastMessage'); return el && (el.innerText.toLowerCase().includes('account') || el.innerText.toLowerCase().includes('not found') || el.innerText.toLowerCase().includes('failed') || el.innerText.toLowerCase().includes('error')); }", timeout=5000)
        invalid_user_toast = page.text_content("#toastMessage")
        assert "account" in invalid_user_toast.lower() or "not found" in invalid_user_toast.lower() or "error" in invalid_user_toast.lower() or "failed" in invalid_user_toast.lower()
        print("[OK] TEST F — DIRECT PASSWORD RESET SECURITY: Nonexistent account properly rejected!")

        browser.close()
        
        print("\n====================================================")
        print("MANDATORY E2E BROWSER ACCEPTANCE SUITE A THROUGH F PASSED 100%")
        print("Console Errors Count:", len(console_errors))
        print("Failed Requests Count:", len(failed_requests))
        print("====================================================")

if __name__ == "__main__":
    test_mandatory_suite_a_through_f()
