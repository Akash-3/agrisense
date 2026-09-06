import os
import sys
import shutil
import zipfile
import subprocess
import glob

def compile_native_apk():
    print("=================================================================")
    print("RE-COMPILING AGRISENSE.APK WITH FORMAL PRODUCTION RELEASE KEYSTORE")
    print("=================================================================")

    java_home = r"C:\Program Files\Android\Android Studio\jbr"
    java_exe = os.path.join(java_home, "bin", "java.exe")
    javac_exe = os.path.join(java_home, "bin", "javac.exe")
    keytool_exe = os.path.join(java_home, "bin", "keytool.exe")

    sdk_dir = r"C:\Users\tempm\AppData\Local\Android\Sdk"
    build_tools_dir = os.path.join(sdk_dir, "build-tools", "33.0.1")
    android_jar = os.path.join(sdk_dir, "platforms", "android-34", "android.jar")

    aapt2_exe = os.path.join(build_tools_dir, "aapt2.exe")
    zipalign_exe = os.path.join(build_tools_dir, "zipalign.exe")
    apksigner_bat = os.path.join(build_tools_dir, "apksigner.bat")
    d8_jar = os.path.join(build_tools_dir, "lib", "d8.jar")

    work_dir = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\apk_build_temp"
    if os.path.exists(work_dir):
        try:
            shutil.rmtree(work_dir)
        except Exception:
            pass
    os.makedirs(work_dir, exist_ok=True)

    output_apk_path = r"C:\Users\tempm\Downloads\AgriSense.apk"
    if os.path.exists(output_apk_path):
        try:
            os.remove(output_apk_path)
        except Exception:
            pass

    # 1. Create clean AndroidManifest.xml
    manifest_dst = os.path.join(work_dir, "AndroidManifest.xml")
    with open(manifest_dst, "w", encoding="utf-8") as f:
        f.write('''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.agrisense.app"
    android:versionCode="1"
    android:versionName="1.0.0">
    
    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />
    
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
    
    <application
        android:allowBackup="true"
        android:label="AgriSense"
        android:supportsRtl="true"
        android:theme="@android:style/Theme.NoTitleBar.Fullscreen"
        android:usesCleartextTraffic="true">
        <activity
            android:name=".MainActivity"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>''')

    # 2. Prepare Assets (offline index.html)
    assets_dir = os.path.join(work_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    html_src = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\app\frontend\index.html"
    shutil.copy(html_src, os.path.join(assets_dir, "index.html"))

    # 3. Link with AAPT2
    base_apk = os.path.join(work_dir, "base.apk")

    print("Building base APK package with AAPT2...")
    cmd_link = [
        aapt2_exe, "link",
        "-o", base_apk,
        "-I", android_jar,
        "--manifest", manifest_dst,
        "-A", assets_dir,
        "--min-sdk-version", "21",
        "--target-sdk-version", "34",
        "--auto-add-overlay"
    ]
    res_link = subprocess.run(cmd_link, capture_output=True, text=True)
    if res_link.returncode != 0:
        print("AAPT2 Link Error:", res_link.stderr)
        return False

    # 4. Compile Java Sources to Java 8 bytecode
    java_src_dir = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\app\android\app\src\main\java\com\agrisense\app"
    java_file = os.path.join(java_src_dir, "MainActivity.java")
    
    classes_out_dir = os.path.join(work_dir, "classes_out")
    os.makedirs(classes_out_dir, exist_ok=True)

    print("Compiling Java source code to Java 8 bytecode...")
    cmd_javac = [
        javac_exe,
        "-g",
        "-source", "1.8",
        "-target", "1.8",
        "-cp", android_jar,
        "-d", classes_out_dir,
        java_file
    ]
    res_javac = subprocess.run(cmd_javac, capture_output=True, text=True)
    if res_javac.returncode != 0:
        print("Javac Error:", res_javac.stderr)
        return False

    # 5. Convert Java Classes to Android Dex (d8)
    print("Converting Java classes to Android DEX format...")
    dex_out_dir = os.path.join(work_dir, "dex_out")
    os.makedirs(dex_out_dir, exist_ok=True)

    class_files = glob.glob(os.path.join(classes_out_dir, "**", "*.class"), recursive=True)

    cmd_d8 = [java_exe, "-cp", d8_jar, "com.android.tools.r8.D8", "--min-api", "21", "--output", dex_out_dir, "--lib", android_jar] + class_files
    res_d8 = subprocess.run(cmd_d8, capture_output=True, text=True)
    if res_d8.returncode != 0:
        print("D8 Error:", res_d8.stderr)
        return False

    classes_dex = os.path.join(dex_out_dir, "classes.dex")

    # 6. Inject classes.dex into base.apk
    unaligned_apk = os.path.join(work_dir, "unaligned.apk")
    shutil.copy(base_apk, unaligned_apk)

    with zipfile.ZipFile(unaligned_apk, "a") as zipf:
        zipf.write(classes_dex, "classes.dex")

    # 7. Align APK with zipalign
    print("Aligning APK with zipalign...")
    aligned_apk = os.path.join(work_dir, "aligned.apk")
    cmd_zipalign = [zipalign_exe, "-f", "-p", "4", unaligned_apk, aligned_apk]
    res_align = subprocess.run(cmd_zipalign, capture_output=True, text=True)
    if res_align.returncode != 0:
        print("Zipalign Error:", res_align.stderr)
        return False

    # 8. Create Formal Release Keystore & Sign APK with apksigner
    keystore_path = os.path.join(work_dir, "release.keystore")
    if os.path.exists(keystore_path):
        os.remove(keystore_path)

    print("Generating Formal Production Release Keystore...")
    cmd_keytool = [
        keytool_exe, "-genkeypair",
        "-keystore", keystore_path,
        "-storepass", "AgriSense2026",
        "-alias", "agrisense_key",
        "-keypass", "AgriSense2026",
        "-keyalg", "RSA",
        "-keysize", "2048",
        "-validity", "10000",
        "-dname", "CN=AgriSense Platform, OU=AgriSense Systems, O=AgriSense Technologies, L=Mumbai, ST=Maharashtra, C=IN"
    ]
    subprocess.run(cmd_keytool, capture_output=True, text=True)

    print("Signing APK with Production Release Key...")
    env_copy = os.environ.copy()
    env_copy["JAVA_HOME"] = java_home
    env_copy["PATH"] = os.path.join(java_home, "bin") + ";" + env_copy.get("PATH", "")

    cmd_sign = [
        apksigner_bat, "sign",
        "--ks", keystore_path,
        "--ks-pass", "pass:AgriSense2026",
        "--key-pass", "pass:AgriSense2026",
        "--v1-signing-enabled", "true",
        "--v2-signing-enabled", "true",
        "--v3-signing-enabled", "true",
        "--out", output_apk_path,
        aligned_apk
    ]
    res_sign = subprocess.run(cmd_sign, capture_output=True, text=True, shell=True, env=env_copy)
    if res_sign.returncode != 0:
        print("Apksigner Error:", res_sign.stderr)
        return False

    print("=================================================================")
    print("SUCCESS! RELEASE SIGNED AGRISENSE.APK GENERATED AT:")
    print(f"Path: {output_apk_path} ({os.path.getsize(output_apk_path)} bytes)")
    print("=================================================================")
    return True

if __name__ == "__main__":
    compile_native_apk()
