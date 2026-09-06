import os
import sys
import re
import shutil
import subprocess
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FLUTTER_DIR = os.path.join(PROJECT_ROOT, "seashark_dart_app")
PUBSPEC_PATH = os.path.join(FLUTTER_DIR, "pubspec.yaml")
MAIN_DART_PATH = os.path.join(FLUTTER_DIR, "lib", "main.dart")
GRADLE_KTS_PATH = os.path.join(FLUTTER_DIR, "android", "app", "build.gradle.kts")
DOWNLOADS_DIR = r"C:\Users\tempm\Downloads"

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

    # 2. Sync lib/main.dart
    if os.path.exists(MAIN_DART_PATH):
        with open(MAIN_DART_PATH, "r", encoding="utf-8") as f:
            main_content = f.read()
        main_content = re.sub(r'final String _currentAppVersion = "[^"]+";', f'final String _currentAppVersion = "{new_ver_name}";', main_content)
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
    print(f"\n[BUILD ENGINE] Executing Flutter APK compilation for v{new_ver_name} (Build {new_ver_code})...")
    flutter_bat = r"C:\src\flutter\bin\flutter.bat"
    res = subprocess.run([flutter_bat, "build", "apk", "--debug"], cwd=FLUTTER_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        print("[BUILD FAILED] Standard Error:")
        print(res.stderr)
        sys.exit(1)
    print(f"[BUILD ENGINE] Successfully compiled debug APK for AgriSense v{new_ver_name}!")

    # 5. Copy output APKs to Downloads
    apk_source = os.path.join(FLUTTER_DIR, "build", "app", "outputs", "flutter-apk", "app-debug.apk")
    versioned_apk = os.path.join(DOWNLOADS_DIR, f"AgriSense_v{new_ver_name}.apk")
    generic_apk = os.path.join(DOWNLOADS_DIR, "AgriSense.apk")

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    shutil.copyfile(apk_source, versioned_apk)
    shutil.copyfile(apk_source, generic_apk)
    print(f"[DEPLOYMENT] Copied APK to '{versioned_apk}' and '{generic_apk}'")

    print("\n" + "=" * 80)
    print(f" AGRISENSE v{new_ver_name} BUILD & SYNC COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    sync_and_build(target)
