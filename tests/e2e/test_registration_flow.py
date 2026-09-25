import os
import sys
import time
import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("APP_URL", "http://localhost:8000")

def test_full_registration_and_farm_wizard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        
        page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}"))
        page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
        
        # 1. Open Auth Page
        page.goto(BASE_URL, wait_until="networkidle")
        time.sleep(1)
        
        # 2. Switch to Register tab
        register_tab = page.query_selector("button:has-text('Register')")
        if register_tab:
            register_tab.click()
            time.sleep(0.5)
        
        # 3. Fill in registration credentials
        test_email = f"farmer_{int(time.time())}@agrisense.test"
        page.fill("#regName", "Akash Farmer")
        page.fill("#regEmail", test_email)
        page.select_option("#regGender", "Male")
        page.fill("#regAge", "34")
        page.fill("#regPass", "SecureAgri123!")
        
        # 4. Click 'Next: Configure Farm'
        configure_btn = page.query_selector("button:has-text('Next: Configure Farm')")
        assert configure_btn is not None, "Configure Farm button not found"
        configure_btn.click()
        time.sleep(1)
        
        # 5. Verify Farm Setup Wizard modal opens
        wizard = page.query_selector("#farmWizardOverlay")
        assert wizard is not None, "Farm wizard overlay element not found"
        is_visible = page.evaluate("!document.getElementById('farmWizardOverlay').classList.contains('hidden')")
        assert is_visible, "Farm wizard overlay should be visible"
        
        # 6. Interact with map (click 3 points)
        map_box = page.query_selector("#wizardMap")
        assert map_box is not None, "Wizard map container not found"
        box = map_box.bounding_box()
        assert box is not None and box["width"] > 0 and box["height"] > 0, f"Map box invalid: {box}"
        
        # Click 3 points on the map
        page.mouse.click(box["x"] + 100, box["y"] + 100)
        time.sleep(0.3)
        page.mouse.click(box["x"] + 150, box["y"] + 120)
        time.sleep(0.3)
        page.mouse.click(box["x"] + 120, box["y"] + 160)
        time.sleep(0.5)
        
        # Check calculated acreage
        acreage_text = page.text_content("#wizardAcreageDisplay")
        print(f"Calculated Acreage Display: {acreage_text}")
        assert "0.00" not in acreage_text, f"Acreage should update after clicking 3 points, got: {acreage_text}"
        
        # 7. Click 'Complete Setup'
        complete_btn = page.query_selector("button:has-text('Complete Setup')")
        assert complete_btn is not None, "Complete Setup button not found"
        complete_btn.click()
        
        time.sleep(3)
        
        toast_el = page.query_selector("#toast")
        if toast_el:
            print("Toast Message:", toast_el.text_content())
            
        main_screen_hidden = page.evaluate("document.getElementById('mainAppScreen').classList.contains('hidden')")
        print("Main screen hidden?", main_screen_hidden)
        
        auth_screen_hidden = page.evaluate("document.getElementById('authScreen').classList.contains('hidden')")
        print("Auth screen hidden?", auth_screen_hidden)
        
        user_display = page.evaluate("window.AgriState.currentUser")
        print("Registered User in AgriState:", user_display)
        
        browser.close()

if __name__ == "__main__":
    test_full_registration_and_farm_wizard()
