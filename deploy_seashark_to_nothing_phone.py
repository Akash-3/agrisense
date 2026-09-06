import os
import sys
import shutil
import subprocess

def deploy_to_nothing_phone():
    print("=================================================================")
    print("DEPLOYING AGRISENSE SEASHARK APP TO NOTHING PHONE 3")
    print("=================================================================")

    app_dir = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\seashark_dart_app"
    wrapper_props = os.path.join(app_dir, "android", "gradle", "wrapper", "gradle-wrapper.properties")

    # 1. Update gradle-wrapper.properties to Gradle 8.3
    with open(wrapper_props, "w", encoding="utf-8") as f:
        f.write("""distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-8.3-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
""")
    print("Updated gradle-wrapper.properties to Gradle 8.3")

    # 2. Configure Environment for Java 17 (JBR)
    java_home = r"C:\Program Files\Android\Android Studio\jbr"
    env = os.environ.copy()
    env["JAVA_HOME"] = java_home
    env["PATH"] = os.path.join(java_home, "bin") + ";" + env.get("PATH", "")

    # 3. Stop old Gradle Daemons running on Java 25
    print("Stopping background daemons...")
    subprocess.run(["cmd", "/c", "gradlew", "--stop"], cwd=os.path.join(app_dir, "android"), env=env)

    # 4. ADB Port Forwarding tcp:8000 -> tcp:8000
    sdk_adb = r"C:\Users\tempm\AppData\Local\Android\Sdk\platform-tools\adb.exe"
    if os.path.exists(sdk_adb):
        subprocess.run([sdk_adb, "reverse", "tcp:8000", "tcp:8000"], capture_output=True, text=True)
        print("ADB Port Forwarding tcp:8000 -> tcp:8000 active!")

    # 5. Launch Flutter run on Nothing Phone 3
    print("Building and deploying to Nothing Phone 3 (A024)...")
    flutter_bin = r"C:\src\flutter\bin\flutter.bat"
    if not os.path.exists(flutter_bin):
        flutter_bin = "flutter.bat"

    res = subprocess.run([flutter_bin, "run", "-d", "A024"], cwd=app_dir, env=env)
    print(f"Deployment Exit Code: {res.returncode}")

if __name__ == "__main__":
    deploy_to_nothing_phone()
