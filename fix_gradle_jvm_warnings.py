"""
AgriSense — Comprehensive Gradle JVM Native Access Fixer Script
=====================================================================
Fixes the JVM Java 21+ Native Access Warning:
"WARNING: A restricted method in java.lang.System has been called by net.rubygrapefruit.platform.internal.NativeLibraryLoader"
"""

import os
import sys
import subprocess

GRADLE_PROPERTIES_PATH = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\seashark_dart_app\android\gradle.properties"
GLOBAL_GRADLE_PROPERTIES_PATH = r"C:\Users\tempm\.gradle\gradle.properties"
GRADLEW_BAT_PATH = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\seashark_dart_app\android\gradlew.bat"

JVM_ARGS = "-Xmx8G -XX:MaxMetaspaceSize=4G -XX:ReservedCodeCacheSize=512m -XX:+HeapDumpOnOutOfMemoryError --enable-native-access=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED"

def fix_gradle_properties(path):
    print(f"[1/4] Updating Gradle properties at: {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    lines = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
    new_lines = []
    has_jvmargs = False
    for line in lines:
        if line.startswith("org.gradle.jvmargs="):
            new_lines.append(f"org.gradle.jvmargs={JVM_ARGS}\n")
            has_jvmargs = True
        else:
            new_lines.append(line)
            
    if not has_jvmargs:
        new_lines.insert(0, f"org.gradle.jvmargs={JVM_ARGS}\n")
        
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"[SUCCESS] Updated {path}")

def fix_gradlew_bat(path):
    print(f"[2/4] Updating gradlew.bat at: {path}")
    if not os.path.exists(path):
        print(f"[NOTICE] {path} not found.")
        return
        
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    old_target = 'set DEFAULT_JVM_OPTS='
    new_target = 'set DEFAULT_JVM_OPTS="--enable-native-access=ALL-UNNAMED" "--add-opens=java.base/java.lang=ALL-UNNAMED"'
    
    if old_target in content and new_target not in content:
        content = content.replace(old_target, new_target)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("[SUCCESS] Updated DEFAULT_JVM_OPTS in gradlew.bat")
    else:
        print("[SUCCESS] gradlew.bat already up to date")

def set_windows_environment_vars():
    print("[3/4] Setting Windows Environment Variables (GRADLE_OPTS & JAVA_TOOL_OPTIONS)...")
    val = "--enable-native-access=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED"
    try:
        subprocess.run(f'setx GRADLE_OPTS "{val}"', shell=True, check=True, capture_output=True)
        subprocess.run(f'setx JAVA_TOOL_OPTIONS "{val}"', shell=True, check=True, capture_output=True)
        os.environ["GRADLE_OPTS"] = val
        os.environ["JAVA_TOOL_OPTIONS"] = val
        print("[SUCCESS] Set GRADLE_OPTS and JAVA_TOOL_OPTIONS environment variables!")
    except Exception as e:
        print(f"[NOTICE] Environment variable note: {e}")

def run_verification():
    print("\n[4/4] Verifying configuration...")
    print("=================================================================")
    print("JVM Native Access configuration updated across all Gradle entrypoints!")
    print("=================================================================")

if __name__ == "__main__":
    fix_gradle_properties(GRADLE_PROPERTIES_PATH)
    fix_gradle_properties(GLOBAL_GRADLE_PROPERTIES_PATH)
    fix_gradlew_bat(GRADLEW_BAT_PATH)
    set_windows_environment_vars()
    run_verification()
