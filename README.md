# AgriSense - Autonomous Agriculture & Precision Farming Platform

AgriSense is an AI-powered enterprise smart agriculture platform for real-time soil telemetry monitoring, crop disease diagnosis, autonomous drone fleet control, and precision farm management.

---

## 🌟 Key Platform Features

- **Interactive Web Dashboard**: Real-time soil moisture (VWC), ambient temperature, relative humidity, air quality (MQ-135), and solar irradiance monitoring with pre-symptomatic fungal stress prediction.
- **Real Browser-Autofilled Google & Microsoft SSO**: Interactive provider-branded SSO modal dialog supporting native browser email autofill (`autocomplete="email"` and `autocomplete="name"`) for instant account registration and sign-in.
- **100% Real Hardware Telemetry Engine**: Operates strictly on physical ESP32 multi-sensor payloads (Soil Moisture, DHT22 Temp/Humidity, MQ-135 Air Quality) with instant hardware fault detection (`SENSOR_DISCONNECTED`).
- **User Address & Dynamic Country Dial Codes**: Country selector (`#profCountry`) automatically formatting and prefixing mobile phone dial codes (US `+1`, India `+91`, UK `+44`, etc.) with PostgreSQL & SQLite database persistence.
- **Remote ESP32 IoT Firmware (1,200 km WAN Ready)**: Production C++/Arduino firmware (`esp32/multi_sensor_esp32/multi_sensor_esp32.ino`) with TCP socket clean-up (`http.setReuse(false);` & `Connection: close`) and Google DNS fallback (`8.8.8.8`).
- **Live Crop Health AI Scanner**: Leaf photo analysis for computer vision disease diagnosis, health index calculation, and treatment recommendations.
- **Automated In-App OTA Updates**: Direct background check, download, and installation of signed APK updates (`/api/v1/update/check`).
- **Autonomous Drone Fleet & Satellite Boundary Mapper**: Interactive Leaflet satellite map with dynamic polygon acreage calculation and waypoint mission planning.

---

## 🚀 How to Launch the Website Locally

### 📋 Prerequisites

1. **Python 3.10+**: Ensure Python is installed (`python --version`).

---

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Akash-3/agrisense.git
cd agrisense
```

---

### 2️⃣ Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

### 3️⃣ Launch the Website Server

Run the main application server entry point:

```bash
python app/run_app.py
```

Upon launching, the script will output local network URLs and automatically open your default browser.

Access the website locally at:
- 🌐 **Web Application Dashboard**: [http://localhost:8000](http://localhost:8000)
- 📚 **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📱 Mobile Application Setup (Optional)

Navigate into the Flutter mobile app directory:

```bash
cd mobile_app
flutter pub get
flutter run
```

To build a standalone production Android APK:

```bash
flutter build apk --release
```

---

## 🔌 Flash ESP32 Multi-Sensor IoT Node

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
├── app/                  # Web Application & Backend Server
│   ├── backend/          # REST Endpoints, SQLite/Postgres DB Engine, Auth, & Telemetry
│   ├── frontend/         # Web Dashboard UI, Leaflet Maps, & State Layer
│   └── run_app.py        # Main Application & Web Dashboard Server Entry Point
├── mobile_app/           # Flutter Cross-Platform Mobile Application (Android/iOS)
│   ├── lib/              # UI Screens, Widgets, Models, & Native Services
│   └── pubspec.yaml      # Flutter Mobile Dependencies
├── esp32/                # Production ESP32 C++/Arduino Firmware & Pre-compiled Binaries
│   ├── multi_sensor_esp32/  # Main ESP32 Sketch Folder
│   └── build/            # Pre-compiled .bin Binaries for esptool Flashing
├── requirements.txt      # Root Python Server Dependencies
└── README.md             # Platform Setup & Architecture Guide
```

---

## 🔒 License & Governance
Developed for the AgriSense Autonomous Agriculture Platform.
