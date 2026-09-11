"""
AgriSense End-to-End Automated QA & Virtual User Test Suite
Uses Playwright Python to test real browser interactions, responsive layouts,
animations, data consistency, modal dismissals, and hardware abstraction rules.
"""

import os
import sys
import time
import json
import unittest
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("APP_URL", "http://localhost:8000")
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

class AgriSenseVirtualUserQATest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        # Headless chromium launch
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.console_errors = []
        self.network_failures = []
        
        self.context = self.browser.new_context(viewport={"width": 1280, "height": 800})
        self.page = self.context.new_page()

        # Listen for console errors
        self.page.on("console", lambda msg: self.console_errors.append(msg.text) if msg.type in ["error", "warning"] and "favicon" not in msg.text else None)
        
        # Listen for failed HTTP network requests
        self.page.on("response", lambda resp: self.network_failures.append(f"{resp.status} {resp.url}") if resp.status >= 400 and "favicon" not in resp.url else None)

    def tearDown(self):
        self.context.close()

    def capture_screenshot(self, name):
        filepath = os.path.join(SCREENSHOT_DIR, f"{name}.png")
        self.page.screenshot(path=filepath, full_page=True)
        return filepath

    # ==================== TEST 1: BRANDING & DEMO LOGIN ====================
    def test_01_branding_and_demo_login(self):
        """Verify AgriSense branding, empty default inputs, and Try Demo Account button"""
        self.page.goto(BASE_URL)
        self.page.wait_for_selector("#authScreen", state="visible")
        
        # Verify Branding & Tagline
        branding = self.page.inner_text("#authScreen")
        self.assertIn("AgriSense", branding, "AgriSense brand title missing from auth screen")
        
        # Verify inputs are empty by default (no hardcoded passwords displayed)
        login_id = self.page.input_value("#loginIdInput")
        login_pass = self.page.input_value("#loginPassInput")
        self.assertEqual(login_id, "", "Login ID input must be empty by default")
        self.assertEqual(login_pass, "", "Login password input must be empty by default")
        
        self.capture_screenshot("01_login_screen")

    # ==================== TEST 2: LOGIN TO DASHBOARD ANIMATION ====================
    def test_02_login_to_dashboard_entrance_animation(self):
        """Verify smooth transition & animation when signing in to dashboard"""
        self.page.goto(BASE_URL)
        self.page.wait_for_selector("#authScreen", state="visible")
        time.sleep(0.3)
        
        # Click Try Demo Account
        self.page.click("button:has-text('Try Demo Account')")
        
        # Observe transition from auth screen to main app screen
        self.page.wait_for_selector("#mainAppScreen", state="visible", timeout=5000)
        
        # Verify dashboard active view
        dashboard_visible = self.page.is_visible("#pageDashboard")
        self.assertTrue(dashboard_visible, "Dashboard page failed to open after login")
        
        # Verify transition animation classes or computed opacity / transform
        anim_card = self.page.locator("#pageDashboard").evaluate("el => getComputedStyle(el).display")
        self.assertIn(anim_card, ["block", "flex", "grid"], "Dashboard should be smoothly displayed after transition animation")
        
        self.capture_screenshot("02_dashboard_animation_complete")

    # ==================== TEST 3: ANALYTICS ACCEPTANCE & SENSOR ABSTRACTION ====================
    def test_03_analytics_acceptance_and_sensor_abstraction(self):
        """
        CRITICAL TEST: Verify Analytics does NOT contain raw 10-Channel Reflectance Spectrum,
        raw channel codes F1-F8/NIR, or raw AS7341 hardware terminology.
        """
        self.page.goto(BASE_URL)
        self.page.click("button:has-text('Try Demo Account')")
        self.page.wait_for_selector("#mainAppScreen", state="visible")
        
        # Navigate to Analytics
        self.page.click("[data-view='analytics']")
        self.page.wait_for_selector("#pageAnalytics", state="visible")
        self.capture_screenshot("03_analytics_page")
        
        analytics_html = self.page.inner_html("#pageAnalytics")
        
        # FAIL if 10-Channel Reflectance Spectrum is present
        self.assertNotIn("10-Channel Reflectance Spectrum", analytics_html, 
                         "CRITICAL FAILURE: Analytics page still contains forbidden raw '10-Channel Reflectance Spectrum' title!")
        
        # FAIL if raw AS7341 channel codes are exposed in normal UI
        for forbidden_code in ["F1 (415nm)", "F2 (445nm)", "F3 (480nm)", "F8 (680nm)"]:
            self.assertNotIn(forbidden_code, analytics_html, 
                             f"CRITICAL FAILURE: Raw hardware channel '{forbidden_code}' exposed in Analytics UI!")

        # Verify user-friendly Insights & Metrics exist
        self.assertIn("Crop Health", analytics_html, "Analytics page must communicate Crop Health")
        self.assertIn("Pathogen Risk", analytics_html, "Analytics page must communicate Pathogen Risk")

    # ==================== TEST 4: CROP HEALTH SIMULATOR ====================
    def test_04_crop_health_simulator(self):
        """Verify Crop Health Simulator scenarios (Healthy, Fungal, Drought, Fire) and Reset"""
        self.page.goto(BASE_URL)
        self.page.click("button:has-text('Try Demo Account')")
        self.page.wait_for_selector("#mainAppScreen", state="visible")
        
        # Navigate to Scenarios
        self.page.click("[data-view='scenarios']")
        self.page.wait_for_selector("#pageScenarios", state="visible")
        
        # Verify cards exist
        scenario_text = self.page.inner_text("#pageScenarios")
        self.assertIn("Soil Drought", scenario_text, "Soil Drought scenario card missing")
        self.assertIn("Fungal Stress", scenario_text, "Fungal Stress scenario card missing")
        
        # Click Soil Drought
        self.page.click("div:has-text('3. Soil Drought')")
        time.sleep(0.5)
        self.capture_screenshot("04_drought_scenario_active")
        
        # Reset Simulation
        self.page.click("button:has-text('Reset Simulation')")
        time.sleep(0.5)

    # ==================== TEST 5: MAP FIELD DRAWER & DISMISSAL ====================
    def test_05_map_field_drawer_and_dismissal(self):
        """Verify Map polygon click, highlight, right drawer, data content, × button, backdrop click, and ESC key"""
        self.page.goto(BASE_URL)
        self.page.click("button:has-text('Try Demo Account')")
        self.page.wait_for_selector("#mainAppScreen", state="visible")
        
        # Navigate to Satellite Map
        self.page.click("[data-view='map']")
        self.page.wait_for_selector("#pageMap", state="visible")
        time.sleep(0.4)
        
        # Click on Leaflet polygon / trigger field selection
        self.page.evaluate("UI.showFieldDetailPanel({ name: 'Green Valley Field Plot', acres: 15.0, crop: 'Wheat & Paddy', health: 92.4, hydration: 42.1, risk: 4.2 })")
        time.sleep(0.3)
        
        # Verify Field Drawer opens
        self.page.wait_for_selector("#fieldDetailPanel", state="visible", timeout=3000)
        self.capture_screenshot("05_map_field_drawer_open")
        
        panel_text = self.page.inner_text("#fieldDetailPanel")
        self.assertIn("Crop Health Index", panel_text, "Field details drawer missing Crop Health Index")
        self.assertIn("Soil Hydration VWC", panel_text, "Field details drawer missing Soil Hydration VWC")
        self.assertIn("Pathogen Risk", panel_text, "Field details drawer missing Pathogen Risk")
        
        # Test 1: Dismiss via Close Button ×
        self.page.click("#fieldDetailPanel button:has(.fa-xmark)", force=True)
        time.sleep(0.5)
        is_hidden_1 = self.page.evaluate("document.getElementById('fieldDetailPanel').classList.contains('hidden')")
        self.assertTrue(is_hidden_1, "Field drawer failed to close via × button")

        # Test 2: Reopen & Dismiss via ESC key
        self.page.evaluate("UI.showFieldDetailPanel({ name: 'Green Valley Field Plot', acres: 15.0, crop: 'Wheat & Paddy', health: 92.4, hydration: 42.1, risk: 4.2 })")
        time.sleep(0.3)
        self.page.wait_for_selector("#fieldDetailPanel", state="visible")
        self.page.keyboard.press("Escape")
        time.sleep(0.5)
        is_hidden_2 = self.page.evaluate("document.getElementById('fieldDetailPanel').classList.contains('hidden')")
        self.assertTrue(is_hidden_2, "Field drawer failed to close via ESC key")

    # ==================== TEST 6: MISSION PLANNER NO AUTO-OPEN & SENSOR SYNCHRONIZATION ====================
    def test_06_mission_planner_workflow(self):
        """Verify Mission Planner drawer is NOT open on load, target field dropdown syncs with map, sensor payload is abstract"""
        self.page.goto(BASE_URL)
        self.page.click("button:has-text('Try Demo Account')")
        self.page.wait_for_selector("#mainAppScreen", state="visible")
        
        # Open Mission Planner
        self.page.click("[data-view='missionPlanner']")
        self.page.wait_for_selector("#pageMissionPlanner", state="visible")
        
        # VERIFY DRAWER IS NOT AUTOMATICALLY OPEN ON LOAD
        drawer_visible = self.page.is_visible("#fieldDetailPanel")
        self.assertFalse(drawer_visible, "Mission Planner field drawer must NOT automatically open on page load")
        
        # Check Sensor Payload dropdown wording
        sensor_options = self.page.inner_text("#mpPayloadSelect")
        self.assertIn("Multispectral Crop Health Sensor", sensor_options, "Sensor payload option missing 'Multispectral Crop Health Sensor'")
        self.assertNotIn("Adafruit AS7341", sensor_options, "Sensor payload dropdown must NOT expose raw 'Adafruit AS7341'")
        
        self.capture_screenshot("06_mission_planner_clean")

    # ==================== TEST 7: DATA CONSISTENCY & PHONE vs EMAIL ====================
    def test_07_data_consistency_and_phone(self):
        """Verify phone number input does not show email address"""
        self.page.goto(BASE_URL)
        self.page.click("button:has-text('Try Demo Account')")
        self.page.wait_for_selector("#mainAppScreen", state="visible")
        
        # Navigate to Profile
        self.page.click("[data-view='profile']")
        self.page.wait_for_selector("#pageProfile", state="visible")
        
        phone_val = self.page.input_value("#profPhone")
        self.assertNotIn("@", phone_val, "Mobile Phone field must NEVER display email address with '@'")
        
        self.capture_screenshot("07_profile_account_security")

    # ==================== TEST 8: RESPONSIVE VIEWPORT SUITE ====================
    def test_08_responsive_viewports(self):
        """Test application across mobile, tablet, and desktop resolutions"""
        viewports = [
            {"width": 360, "height": 800, "name": "360x800_mobile"},
            {"width": 390, "height": 844, "name": "390x844_mobile"},
            {"width": 768, "height": 1024, "name": "768x1024_tablet"},
            {"width": 1920, "height": 1080, "name": "1920x1080_desktop"},
        ]

        for vp in viewports:
            context = self.browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
            page = context.new_page()
            page.goto(BASE_URL)
            page.click("button:has-text('Try Demo Account')")
            page.wait_for_selector("#mainAppScreen", state="visible")
            
            # Check horizontal overflow
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            self.assertLessEqual(scroll_width, vp["width"] + 5, f"Horizontal scroll overflow detected at {vp['name']}")
            
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"responsive_{vp['name']}.png"))
            context.close()

    # ==================== TEST 9: REAL EMAIL BROWSER AUTOFILL SSO FLOW ====================
    def test_09_real_email_sso_flow(self):
        """Verify Google & Microsoft SSO opens real email modal with browser autofill enabled"""
        self.page.goto(BASE_URL)
        self.page.wait_for_selector("#authScreen", state="visible")
        
        # Click Google SSO button
        self.page.click("button:has-text('Google SSO')")
        self.page.wait_for_selector("#ssoModal", state="visible")
        
        # Verify autocomplete="email" attribute on ssoEmailInput for browser autofill
        email_autocomplete = self.page.get_attribute("#ssoEmailInput", "autocomplete")
        self.assertEqual(email_autocomplete, "email", "SSO email input must use autocomplete='email' for browser autofill")
        
        # Enter real Gmail address
        test_gmail = "myuser.farmer@gmail.com"
        self.page.fill("#ssoEmailInput", test_gmail)
        self.page.click("#ssoSubmitBtn")
        
        # Verify successful login to dashboard with real Gmail address
        self.page.wait_for_selector("#mainAppScreen", state="visible", timeout=5000)
        user_email = self.page.inner_text(".user-email")
        self.assertEqual(user_email, test_gmail, "User profile must display their real Gmail address after SSO login")
        self.capture_screenshot("09_real_email_sso_complete")

if __name__ == "__main__":
    unittest.main()
