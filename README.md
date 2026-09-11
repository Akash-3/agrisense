# AgriSense - Autonomous Agriculture & Precision Farming Platform

AgriSense is an AI-powered enterprise smart agriculture platform for real-time soil telemetry monitoring, crop disease diagnosis, autonomous drone fleet control, and precision farm management.

---

## 🌟 Key Platform Features

- **Real Browser-Autofilled Google & Microsoft SSO**: Interactive provider-branded SSO modal dialog supporting native browser email autofill (`autocomplete="email"` and `autocomplete="name"`) for instant real account registration and sign-in.
- **100% Purged Fake Data & Real Hardware Telemetry**: All artificial `Math.random()` data generators purged. Operates strictly on physical ESP32 multi-sensor payloads (Soil Moisture, DHT22 Temp/Humidity, MQ-135 Air Quality).
- **User Address Details & Dynamic International Dial Codes**: Country dropdown selector (`#profCountry`) automatically formatting and prefixing mobile phone dial codes (US `+1`, India `+91`, UK `+44`, etc.) with PostgreSQL & SQLite schema auto-migrations.
- **Remote ESP32 Multi-Sensor IoT Firmware (1,200 km WAN Ready)**: Production C++/Arduino firmware (`esp32/multi_sensor_esp32.ino`) with TCP socket clean-up (`http.setReuse(false);` & `Connection: close`), Google DNS fallback (`8.8.8.8`), and real hardware disconnection detection (`SENSOR_DISCONNECTED`).
- **Virtual User E2E QA Automated Testing System**: Playwright browser automation test suite (`python run_qa_tests.py`) validating 9 critical end-to-end user workflows with 100% test pass guarantee.
- **Live Crop Health AI Scanner**: Leaf photo analysis for computer vision disease diagnosis, health index calculation, and actionable treatment recommendations.
- **Automated In-App OTA Software Updates**: Direct background check, download, and installation of signed APK updates (`/api/v1/update/check`).
- **Autonomous Drone Fleet & Satellite Boundary Mapper**: Interactive Leaflet satellite map with dynamic polygon acreage calculation and waypoint mission planning.

---

## 💻 Manual Setup & Quick Start

### 📋 Prerequisites

1. **Python 3.10+**: Ensure Python is installed (`python --version`).
2. **Playwright for E2E QA**: Installed automatically via `requirements.txt`.

---

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Akash-3/agrisense.git
cd agrisense
```

---

### 2️⃣ Start the Python FastAPI Server

Install dependencies and launch the server:

```bash
pip install -r requirements.txt
python app/run_app.py
```

The server will start at:
- **Web Dashboard**: `http://localhost:8000`
- **Interactive Swagger API Docs**: `http://localhost:8000/docs`

---

### 3️⃣ Execute Automated Virtual User E2E QA Tests

Run the 9-point Playwright end-to-end acceptance suite:

```bash
python run_qa_tests.py
```

---

### 4️⃣ Flash ESP32 Multi-Sensor IoT Node

1. Open `esp32/multi_sensor_esp32/multi_sensor_esp32.ino` in Arduino IDE or VS Code.
2. Update Wi-Fi SSID and Password (`WIFI_SSID`, `WIFI_PASSWORD`).
3. Upload to your ESP32 board or flash pre-compiled binary via `esptool`:

```bash
python -m esptool --port COM3 --baud 921600 write_flash 0x10000 esp32/build/multi_sensor_esp32.ino.bin
```

---

## 📁 Repository Structure

```
agrisense/
├── app/                  # Web Application & Backend API
│   ├── backend/          # REST Endpoints, SQLite/Postgres DB Engine, Auth, & Telemetry
│   ├── frontend/         # Web Dashboard UI, Leaflet Maps, & State Layer
│   └── run_app.py        # Main Application Server Entry Point
├── mobile_app/           # Flutter Cross-Platform Mobile Application (Android/iOS)
│   ├── lib/              # UI Screens, Widgets, Models, & Native Services
│   └── pubspec.yaml      # Flutter Mobile Dependencies
├── esp32/                # Production ESP32 C++/Arduino Firmware & Pre-compiled Binaries
│   ├── multi_sensor_esp32/  # Main ESP32 Sketch Folder
│   └── build/            # Pre-compiled .bin Binaries for esptool Flashing
├── tests/                # Automated Virtual User QA Testing Suite
│   ├── e2e/              # Playwright E2E Browser Acceptance Tests
│   └── simulate_esp32_hardware.py # Virtual ESP32 Hardware Simulator Client
├── run_qa_tests.py       # E2E Test Suite Runner
├── requirements.txt      # Root Python Dependencies
└── README.md             # Platform Setup & Architecture Guide
```

---

## 🔒 License & Governance
Developed for the AgriSense Autonomous Agriculture Platform.
