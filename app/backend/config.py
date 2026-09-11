import os
from database import sanitize_input

def load_latest_app_version():
    try:
        pubspec_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mobile_app", "pubspec.yaml"))
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
    return "1.7.8", 33

def get_existing_apk_path():
    project_apk = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mobile_app", "build", "app", "outputs", "flutter-apk", "app-debug.apk"))
    ver_name, _ = load_latest_app_version()
    user_downloads = os.path.expanduser("~/Downloads")
    candidates = [
        project_apk,
        os.path.join(user_downloads, f"AgriSense_v{ver_name}.apk"),
        os.path.join(user_downloads, "AgriSense.apk"),
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
