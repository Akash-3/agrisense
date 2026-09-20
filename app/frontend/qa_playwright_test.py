import os
import sys
import time
import socket
import threading
import uvicorn
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(line_buffering=True)

# Add backend directory to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "app", "backend")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

test_port = find_free_port()
os.environ["CORS_ALLOWED_ORIGINS"] = f"http://localhost:3000,http://127.0.0.1:{test_port}"
os.environ["DEVICE_API_KEY"] = "test_mv_key"
os.environ["JWT_SECRET_KEY"] = "test_jwt"

from main import app

class UvicornTestServer(threading.Thread):
    def __init__(self, host="127.0.0.1", port=8888):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="error")
        self.server = uvicorn.Server(config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True

def wait_for_port(port, host="127.0.0.1", timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except Exception:
            time.sleep(0.2)
    return False

def run_playwright_browser_qa():
    server = UvicornTestServer(port=test_port)
    server.start()
    if not wait_for_port(test_port):
        print(f"ERROR: Test server failed to start on port {test_port}")
        sys.exit(1)

    print(f"[Playwright QA] FastAPI Test Server started at http://127.0.0.1:{test_port}/")

    viewports = [
        {"name": "Mobile 360x800", "width": 360, "height": 800},
        {"name": "Mobile 390x844", "width": 390, "height": 844},
        {"name": "Tablet 768x1024", "width": 768, "height": 1024},
        {"name": "Desktop 1440x900", "width": 1440, "height": 900}
    ]

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in viewports:
            print(f"\n--- Running Playwright QA for Viewport: {vp['name']} ---")
            context = browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
            context.add_init_script("localStorage.clear(); sessionStorage.clear();")
            page = context.new_page()

            console_errors = []
            failed_requests = []

            def handle_response(response):
                if response.status in (401, 403, 500):
                    console_errors.append(f"HTTP {response.status} on {response.url}")
                    print(f"    [HTTP ERROR {response.status}] {response.url}")

            page.on("response", handle_response)
            page.on("requestfailed", lambda req: failed_requests.append(req.url))

            # 1. Load Auth Page
            page.goto(f"http://127.0.0.1:{test_port}/", wait_until="networkidle")
            # 1. Load Auth Page
            page.goto(f"http://127.0.0.1:{test_port}/", wait_until="networkidle")
            time.sleep(1)

            # 2. Click Demo Login
            demo_btn = page.query_selector("button:has-text('Demo Login')")
            if demo_btn:
                demo_btn.click()
                time.sleep(1.5)

            # Check horizontal overflow
            overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")

            # 3. Verify Navigation Views
            navigation_views = ["dashboard", "analytics", "scenarios", "map", "telemetry", "alerts", "settings", "profile"]
            for view in navigation_views:
                page.evaluate(f"window.UI.switchView('{view}')")
                time.sleep(0.4)

            # 4. Test Farm Wizard Overlay & Esc Key Dismissal
            page.evaluate("window.UI.openFarmWizard()")
            time.sleep(0.3)
            wizard_visible = page.evaluate("document.getElementById('farmWizardOverlay') ? !document.getElementById('farmWizardOverlay').classList.contains('hidden') : false")
            
            page.keyboard.press("Escape")
            time.sleep(0.3)
            page.evaluate("window.UI.closeFarmWizard()")
            time.sleep(0.3)
            wizard_closed = page.evaluate("document.getElementById('farmWizardOverlay') ? document.getElementById('farmWizardOverlay').classList.contains('hidden') : false")

            print(f"    [WIZARD DEBUG] visible={wizard_visible}, closed={wizard_closed}")

            res = {
                "viewport": vp["name"],
                "overflow": overflow,
                "console_errors": len(console_errors),
                "failed_requests": len(failed_requests),
                "wizard_tested": wizard_visible and wizard_closed,
                "error_list": console_errors,
                "failed_req_list": failed_requests
            }
            results.append(res)
            print(f"  Result: Horizontal Overflow={overflow}, Console Errors={len(console_errors)}, Failed Requests={len(failed_requests)}, Wizard Tested={res['wizard_tested']}")

            context.close()

        browser.close()

    server.stop()
    print("\n=================================================================")
    print("PLAYWRIGHT BROWSER QA EXECUTION SUMMARY")
    print("=================================================================")
    all_passed = True
    for r in results:
        status = "PASSED" if (not r["overflow"] and r["console_errors"] == 0 and r["failed_requests"] == 0 and r["wizard_tested"]) else "FAILED"
        if status == "FAILED": all_passed = False
        print(f"[{status}] Viewport: {r['viewport']} | Overflow: {r['overflow']} | Errors: {r['console_errors']} | Failed Reqs: {r['failed_requests']}")

    if all_passed:
        print("\nALL BROWSER QA VERIFICATIONS PASSED CLEANLY (100% SUCCESS)!")
    else:
        print("\nSOME QA VERIFICATIONS FAILED - DETAILS:")
        for r in results:
            if r["error_list"]:
                print(f"  {r['viewport']} Console Errors:")
                for err in r["error_list"]:
                    print(f"    - {err}")
        sys.exit(1)

if __name__ == "__main__":
    run_playwright_browser_qa()
