# AgriSense - Next-Gen Precision Agriculture & Smart Farming Platform

AgriSense is an AI-powered smart agriculture platform for real-time soil telemetry monitoring, crop disease diagnosis, drone fleet control, and automated farm management.

---

## 🌟 Key Features

- **Real-Time Telemetry & AI Diagnosis**: Live monitoring of soil moisture (VWC), ambient temperature, relative humidity, air quality (MQ-135), and solar irradiance with pre-symptomatic fungal stress prediction.
- **Dynamic Local Time Greeting**: Custom greeting based on device local time (`Good Morning`, `Good Afternoon`, `Good Evening`).
- **Location-Based Live Weather**: Automatic GPS location recognition with real-time Open-Meteo weather forecasting.
- **ESP32 IoT Ingestion**: High-performance HTTP ingest endpoints (`/api/v1/telemetry/ingest`) for ESP32 and edge sensor devices.
- **Google & Microsoft SSO + PBKDF2 Security**: Server-side email normalization, salted PBKDF2 password hashing, and OAuth SSO integration.
- **Automated OTA Software Updates**: Direct in-app background download and streamed installation of APK updates (`/api/v1/update/check`).
- **Autonomous Drone Station & Field Boundary Mapper**: Interactive satellite terrain maps with polygon acreage calculation and flight path dispatching.

---

## 🚀 Setup & Installation Guide for a New Laptop

Follow these simple steps to install and run AgriSense on any new computer or laptop.

### 📋 Prerequisites

1. **Python 3.10+**: Ensure Python is installed (`python --version`).
2. **Flutter SDK 3.x+**: (Optional for mobile development) Ensure Flutter is installed (`flutter --version`).
3. **Android Studio / ADB**: (Optional) For deploying APKs to physical Android phones or emulators.

---

### 1️⃣ Clone the Repository

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd agrisense
```

---

### 2️⃣ Start the Python FastAPI Backend

Install the Python dependencies and launch the backend server:

```bash
pip install -r requirements.txt
python app/run_app.py
```

The backend server will start at:
- **REST API & WebSockets**: `http://localhost:8000`
- **Interactive Swagger Documentation**: `http://localhost:8000/docs`

---

### 3️⃣ Run or Build the Flutter Mobile App

Navigate into the Flutter application folder:

```bash
cd seashark_dart_app
flutter pub get
flutter run
```

#### To Compile a Standalone Release APK:

From the root directory, execute the SSOT release builder script:

```bash
python build_release.py 1.7.0
```

The compiled APK will be output to `C:\Users\<username>\Downloads\AgriSense_v1.7.0.apk`.

---

### 4️⃣ Run Automated Virtual User Verification Suite

To verify that all backend endpoints, authentication guards, lowercased email handlers, ESP32 ingest endpoints, and OTA update services are functioning 100% cleanly:

```bash
python test_virtual_user.py
```

---

## 📁 Repository Structure

```
agrisense/
├── app/                  # FastAPI Backend Server & Database Modules
│   ├── backend/          # REST endpoints, SQLite DB, Auth, & Telemetry Simulator
│   └── run_app.py        # Main backend entry point
├── seashark_dart_app/    # Flutter Cross-Platform Mobile Application
│   ├── lib/              # UI screens, widgets, models, & WebSocket services
│   └── pubspec.yaml      # Flutter dependencies
├── esp32/                # ESP32 C++/Arduino Soil Sensor Firmware & Hardware Diagrams
├── docs/                 # System Architecture & Documentation
├── build_release.py      # Unified SSOT APK Build & Version Sync Automation
├── test_virtual_user.py  # End-to-End Automated Virtual User Testing Suite
├── requirements.txt      # Root Python Dependencies
└── README.md             # Setup & Architecture Guide
```

---

## 🔒 License & Usage
Developed for AgriSense Precision Agriculture Platform.
