plugins {
    id("com.android.application")
    id("dev.flutter.flutter-gradle-plugin")
}

val flutterVersionCode = project.findProperty("flutter-version-code")?.toString()?.toInt() ?: 25
val flutterVersionName = project.findProperty("flutter-version-name")?.toString() ?: "1.7.0"

android {
    namespace = "com.example.agrisense_seashark_app"
    compileSdk = 36
    ndkVersion = "28.2.13676358"

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "com.example.agrisense_seashark_app"
        minSdk = flutter.minSdkVersion
        targetSdk = 36
        versionCode = flutterVersionCode
        versionName = flutterVersionName
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}

flutter {
    source = "../.."
}
