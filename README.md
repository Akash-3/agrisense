# AgriSense - Next-Gen Precision Agriculture & Smart Farming Platform

AgriSense is an AI-powered smart agriculture platform for real-time soil telemetry monitoring, crop disease diagnosis, drone fleet control, and automated farm management.

---

## 🌟 Key Features

- **Live Crop Health AI Scanner**: Snap leaf photos using physical camera or photo gallery for instant AI computer vision disease diagnosis, health score analysis, and actionable remedy treatment plans.
- **Real-Time Telemetry & AI Diagnosis**: Live monitoring of soil moisture (VWC), ambient temperature, relative humidity, air quality (MQ-135), and solar irradiance with pre-symptomatic fungal stress prediction.
- **Dynamic Local Time Greeting**: Custom greeting based on device local time (`Good Morning`, `Good Afternoon`, `Good Evening`).
- **Location-Based Live Weather**: Automatic GPS location recognition with real-time Open-Meteo weather forecasting.
- **ESP32 IoT Ingestion**: High-performance HTTP ingest endpoints (`/api/v1/telemetry/ingest`) for ESP32 and edge sensor devices.
- **Google & Microsoft SSO + PBKDF2 Security**: Server-side email normalization, salted PBKDF2 password hashing, and OAuth SSO integration.
- **Automated OTA Software Updates**: Direct in-app background download and streamed installation of APK updates (`/api/v1/update/check`).
- **Autonomous Drone Station & Field Boundary Mapper**: Interactive satellite terrain maps with polygon acreage calculation and flight path dispatching.

---

## 💻 Manual Setup & Installation Guide

### 📋 Prerequisites

1. **Python 3.10+**: Ensure Python is installed (`python --version`).
2. **Flutter SDK 3.x+**: Ensure Flutter is installed (`flutter --version`).
3. **Android Studio / ADB**: (Optional) For deploying APKs to physical Android phones or emulators.

---

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Akash-3/agrisense.git
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

```bash
cd seashark_dart_app
flutter build apk --release
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
├── requirements.txt      # Root Python Dependencies
└── README.md             # Setup & Architecture Guide
```

---

## 🔒 License & Usage
Developed for AgriSense Precision Agriculture Platform.
