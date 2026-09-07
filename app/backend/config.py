import os
from database import sanitize_input

def load_latest_app_version():
    try:
        pubspec_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "seashark_dart_app", "pubspec.yaml"))
        if os.path.exists(pubspec_path):
            with open(pubspec_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("version:"):
                        val = line.split(":")[1].strip()
                        parts = val.split("+")
                        ver_name = parts[0].strip()
                        ver_code = int(parts[1].strip()) if len(parts) > 1 else 1
                        return ver_name, ver_code
    except Exception as e:
        print(f"[SSOT VERSION LOADER ERROR] {e}")
    return "1.7.4", 29

LATEST_APP_VERSION, LATEST_VERSION_CODE = load_latest_app_version()

def get_existing_apk_path():
    candidates = [
        r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\seashark_dart_app\build\app\outputs\flutter-apk\app-debug.apk",
        f"C:\\Users\\tempm\\Downloads\\AgriSense_v{LATEST_APP_VERSION}.apk",
        r"C:\Users\tempm\Downloads\AgriSense.apk",
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.getsize(p) > 10 * 1024 * 1024:
            return p
    return candidates[0]

def sanitize_email_or_phone(v: str) -> str:
    cleaned = sanitize_input(v)
    if "@" in cleaned:
        return cleaned.lower()
    return cleaned
