import os
import zipfile

def fix_gradle_files(base_dir):
    print(f"Fixing Gradle build files in: {base_dir}")
    
    # 1. Root build.gradle
    root_gradle = os.path.join(base_dir, "build.gradle")
    with open(root_gradle, "w", encoding="utf-8") as f:
        f.write("""// Top-level build file where you can add configuration options common to all sub-projects/modules.
plugins {
    id 'com.android.application' version '8.1.1' apply false
}
""")

    # 2. App build.gradle
    app_gradle = os.path.join(base_dir, "app", "build.gradle")
    with open(app_gradle, "w", encoding="utf-8") as f:
        f.write("""plugins {
    id 'com.android.application'
}

android {
    namespace 'com.agrisense.app'
    compileSdk 34

    defaultConfig {
        applicationId "com.agrisense.app"
        minSdk 21
        targetSdk 34
        versionCode 1
        versionName "1.0.0"
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }
}

dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.9.0'
}
""")

    # 3. settings.gradle
    settings_gradle = os.path.join(base_dir, "settings.gradle")
    with open(settings_gradle, "w", encoding="utf-8") as f:
        f.write("""pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "AgriSense"
include ':app'
""")

    # 4. gradle/wrapper/gradle-wrapper.properties
    wrapper_dir = os.path.join(base_dir, "gradle", "wrapper")
    os.makedirs(wrapper_dir, exist_ok=True)
    wrapper_props = os.path.join(wrapper_dir, "gradle-wrapper.properties")
    with open(wrapper_props, "w", encoding="utf-8") as f:
        f.write("""distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-8.0-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
""")

    print(f"Successfully updated Gradle files for {base_dir}")

if __name__ == "__main__":
    dir1 = r"C:\Users\tempm\Downloads\AgriSense_Android_App"
    dir2 = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\app\android"
    
    fix_gradle_files(dir1)
    fix_gradle_files(dir2)

    # Re-zip
    output_zip = r"C:\Users\tempm\Downloads\AgriSense_Android_App.zip"
    if os.path.exists(output_zip):
        os.remove(output_zip)

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dir1):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, dir1)
                zipf.write(full_path, rel_path)
    print(f"Re-packaged AgriSense_Android_App.zip")
