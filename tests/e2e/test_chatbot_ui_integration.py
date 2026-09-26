import os
import sys
import time
import json
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("APP_URL", "http://127.0.0.1:8000")

def test_chatbot_ui_integration():
    viewports = [
        {"width": 360, "height": 800, "name": "Mobile Small (360x800)"},
        {"width": 390, "height": 844, "name": "Mobile Standard (390x844)"},
        {"width": 768, "height": 1024, "name": "Tablet (768x1024)"},
        {"width": 1440, "height": 900, "name": "Desktop (1440x900)"}
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in viewports:
            print(f"\n--- Testing Viewport: {vp['name']} ---")
            context = browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
            page = context.new_page()

            console_errors = []
            failed_requests = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("requestfailed", lambda req: failed_requests.append(req.url))

            # 1. Open Website
            page.goto(BASE_URL, wait_until="domcontentloaded")
            time.sleep(0.5)

            # 2. Login to Dashboard
            page.fill("#loginIdInput", "qa_farmer@agrisense.io")
            page.fill("#loginPassInput", "Password123!")
            page.click("button:has-text('Sign In to Account')")
            page.wait_for_selector("#mainAppScreen:not(.hidden)", timeout=10000)

            # Check authentication & active farm context
            auth_state = page.evaluate("() => ({ user: window.AgriState.currentUser, activeFarmId: window.AgriState.activeFarmId })")
            assert auth_state["user"] is not None and auth_state["user"]["isAuthenticated"] is True, "User should be authenticated"
            assert auth_state["activeFarmId"] is not None, "Active farm ID must exist"
            print(f"[OK] Authenticated user: {auth_state['user']['name']} (Farm ID: {auth_state['activeFarmId']})")

            # 3. Sidebar toggle on small screens (mobile drawer)
            if vp["width"] < 1024:
                # Click mobile menu button if sidebar hidden
                menu_btn = page.query_selector("button:has(.fa-bars)")
                if menu_btn:
                    menu_btn.click()
                    time.sleep(0.3)

            # 4. Verify AI Assistant nav item is visible
            ai_nav_btn = page.query_selector("button[data-view='chatbot']")
            assert ai_nav_btn is not None, f"AI Assistant button missing in sidebar on {vp['name']}"
            assert ai_nav_btn.is_visible(), f"AI Assistant button not visible on {vp['name']}"
            print(f"[OK] AI Assistant navigation item visible in sidebar ({vp['name']})")

            # 5. Click AI Assistant navigation item
            ai_nav_btn.click()
            time.sleep(0.5)

            # 6. Verify Chatbot UI Window opens & renders
            chat_window = page.query_selector("#agri-chat-window")
            assert chat_window is not None, "Chatbot window element missing"
            assert not page.evaluate("() => document.getElementById('agri-chat-window').classList.contains('hidden')"), "Chatbot window should be visible after clicking AI Assistant"
            print(f"[OK] Chatbot UI window opened successfully ({vp['name']})")

            # 7. Enter message and send query to chatbot endpoint
            test_query = "What is the best fertilizer for wheat crop in North India?"
            page.fill("#agri-chat-input", test_query)
            page.click(".agri-chat-send-btn")

            # Wait for final response message from chatbot API endpoint (ignoring typing indicator)
            page.wait_for_function(
                "() => { const msgs = Array.from(document.querySelectorAll('.bot-msg .msg-bubble')).map(el => el.innerText); return msgs.some(m => !m.includes('Thinking') && !m.includes('Namaste')); }",
                timeout=20000
            )

            bot_responses = page.evaluate("() => Array.from(document.querySelectorAll('.bot-msg .msg-bubble')).map(el => el.innerText)")
            latest_response = bot_responses[-1]
            assert len(latest_response) > 10, f"Chatbot response too short: {latest_response}"
            assert "Thinking" not in latest_response, "Response should not be stuck on typing indicator"
            safe_snippet = latest_response[:60].encode('ascii', 'ignore').decode('ascii')
            print(f"[OK] Chatbot API response received ({len(latest_response)} chars): '{safe_snippet}...'")

            # 8. Verify Console errors and failed chatbot network requests
            chatbot_failed_requests = [r for r in failed_requests if "chatbot" in r]
            assert len(console_errors) == 0, f"Console errors detected on {vp['name']}: {console_errors}"
            assert len(chatbot_failed_requests) == 0, f"Failed chatbot requests on {vp['name']}: {chatbot_failed_requests}"
            print(f"[OK] 0 console errors, 0 failed chatbot requests ({vp['name']})")

            context.close()

        browser.close()
        print("\n====================================================")
        print("ALL CHATBOT UI INTEGRATION BROWSER TESTS PASSED 100%!")
        print("====================================================")

if __name__ == "__main__":
    test_chatbot_ui_integration()
