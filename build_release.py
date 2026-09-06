import os
import sys
import re
import shutil
import subprocess
import socket

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FLUTTER_DIR = os.path.join(PROJECT_ROOT, "seashark_dart_app")
PUBSPEC_PATH = os.path.join(FLUTTER_DIR, "pubspec.yaml")
MAIN_DART_PATH = os.path.join(FLUTTER_DIR, "lib", "main.dart")
GRADLE_KTS_PATH = os.path.join(FLUTTER_DIR, "android", "app", "build.gradle.kts")
DOWNLOADS_DIR = r"C:\Users\tempm\Downloads"
BUILDS_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "AgriSense_Builds")

def get_active_ips():
    ips = []
    # 1. Try tailscale CLI for Tailnet IP
    try:
        res = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.strip().splitlines():
                ip = line.strip()
                if ip and ip not in ips:
                    ips.append(ip)
    except Exception:
        pass

    # 2. Try local socket connection for active Local Wi-Fi/LAN IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        if local_ip and local_ip not in ips:
            ips.append(local_ip)
    except Exception:
        pass

    return ips

def find_flutter_cmd():
    # Check PATH first
    flutter_in_path = shutil.which("flutter")
    if flutter_in_path:
        return flutter_in_path
    
    # Common default installation paths
    default_paths = [
        r"C:\src\flutter\bin\flutter.bat",
        r"C:\flutter\bin\flutter.bat",
        os.path.expanduser(r"~\flutter\bin\flutter.bat"),
    ]
    for path in default_paths:
        if os.path.exists(path):
            return path
    return "flutter"

def sync_and_build(target_version=None):
    print("=" * 80)
    print(" AGRISENSE UNIFIED SINGLE-SOURCE-OF-TRUTH RELEASE BUILDER")
    print("=" * 80)

    # 1. Read / Update pubspec.yaml
    with open(PUBSPEC_PATH, "r", encoding="utf-8") as f:
        pubspec_content = f.read()

    match = re.search(r"version:\s*([0-9\.]+)\+([0-9]+)", pubspec_content)
    if not match:
        raise ValueError("Could not parse version string in pubspec.yaml")

    current_ver_name, current_ver_code = match.group(1), int(match.group(2))

    if target_version and target_version != current_ver_name:
        new_ver_name = target_version
        new_ver_code = current_ver_code + 1
        new_version_line = f"version: {new_ver_name}+{new_ver_code}"
        pubspec_content = re.sub(r"version:\s*[0-9\.]+\+[0-9]+", new_version_line, pubspec_content)
        with open(PUBSPEC_PATH, "w", encoding="utf-8") as f:
            f.write(pubspec_content)
        print(f"[SSOT SYNC] Updated pubspec.yaml -> version: {new_ver_name}+{new_ver_code}")
    else:
        new_ver_name, new_ver_code = current_ver_name, current_ver_code
        print(f"[SSOT SYNC] Using current pubspec.yaml version: {new_ver_name}+{new_ver_code}")

    # 2. Detect Tailnet & Local IPs and update lib/main.dart candidate list & version
    detected_ips = get_active_ips()
    if os.path.exists(MAIN_DART_PATH):
        with open(MAIN_DART_PATH, "r", encoding="utf-8") as f:
            main_content = f.read()
        
        main_content = re.sub(r'final String _currentAppVersion = "[^"]+";', f'final String _currentAppVersion = "{new_ver_name}";', main_content)
        
        if detected_ips:
            print(f"[TAILNET & LOCAL IPs DETECTED] {', '.join(detected_ips)}")
            # Inject detected IPs at the top of candidate list in lib/main.dart if missing
            for ip in reversed(detected_ips):
                candidate_str = f"'{ip}:8000',"
                if candidate_str not in main_content:
                    main_content = main_content.replace(
                        "List<String> candidates = [",
                        f"List<String> candidates = [\n      {candidate_str}"
                    )
            print(f"[SSOT SYNC] Embedded active host candidates into lib/main.dart")

        with open(MAIN_DART_PATH, "w", encoding="utf-8") as f:
            f.write(main_content)
        print(f"[SSOT SYNC] Updated lib/main.dart -> _currentAppVersion = \"{new_ver_name}\"")

    # 3. Sync android/app/build.gradle.kts
    if os.path.exists(GRADLE_KTS_PATH):
        with open(GRADLE_KTS_PATH, "r", encoding="utf-8") as f:
            gradle_content = f.read()
        gradle_content = re.sub(r'val flutterVersionCode = .*', f'val flutterVersionCode = project.findProperty("flutter-version-code")?.toString()?.toInt() ?: {new_ver_code}', gradle_content)
        gradle_content = re.sub(r'val flutterVersionName = .*', f'val flutterVersionName = project.findProperty("flutter-version-name")?.toString() ?: "{new_ver_name}"', gradle_content)
        with open(GRADLE_KTS_PATH, "w", encoding="utf-8") as f:
            f.write(gradle_content)
        print(f"[SSOT SYNC] Updated build.gradle.kts -> versionCode: {new_ver_code}, versionName: {new_ver_name}")

    # 4. Execute Flutter Build APK
    flutter_cmd = find_flutter_cmd()
    print(f"\n[BUILD ENGINE] Executing Flutter APK compilation via '{flutter_cmd}' for v{new_ver_name} (Build {new_ver_code})...")
    res = subprocess.run([flutter_cmd, "build", "apk", "--debug"], cwd=FLUTTER_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        print("[BUILD FAILED] Standard Error:")
        print(res.stderr)
        sys.exit(1)
    print(f"[BUILD ENGINE] Successfully compiled debug APK for AgriSense v{new_ver_name}!")

    # 5. Copy output APKs to dedicated AgriSense_Builds directory and Downloads
    apk_source = os.path.join(FLUTTER_DIR, "build", "app", "outputs", "flutter-apk", "app-debug.apk")
    os.makedirs(BUILDS_OUTPUT_DIR, exist_ok=True)
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    target_apk = os.path.join(BUILDS_OUTPUT_DIR, f"AgriSense_v{new_ver_name}.apk")
    downloads_apk = os.path.join(DOWNLOADS_DIR, f"AgriSense_v{new_ver_name}.apk")

    shutil.copyfile(apk_source, target_apk)
    shutil.copyfile(apk_source, downloads_apk)

    print("\n" + "=" * 80)
    print(f" AGRISENSE v{new_ver_name} BUILD COMPLETE!")
    print(f" [RELEASES FOLDER LOCATION]")
    print(f"    -> {BUILDS_OUTPUT_DIR}")
    print(f" [COMPILED APK FILE]")
    print(f"    -> {target_apk}")
    print("=" * 80)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    sync_and_build(target)
