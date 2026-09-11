# AgriSense 2.0 — Autonomous Multimodal Agricultural Intelligence Platform

AgriSense 2.0 is a research-grade **Autonomous Multimodal Agricultural Intelligence System** integrating 10-channel optical spectroscopy, computer vision canopy spatial imagery, microclimate environmental telemetry, PyTorch deep learning models (`MM-SSNet`), Explainable AI (`Grad-CAM`), density-based spatial clustering (`DBSCAN`), MAVLink/ArduPilot UAV flight planning, closed-loop relay actuation, and Software-In-The-Loop (`SIL`) field digital twin simulation.

---

## 🌟 Research Innovations & Technical Architecture

### 🧠 1. PyTorch MM-SSNet Multimodal Model (`ml/model.py`)
- **Stream 1 (Spectral)**: 1D Convolutional encoder processing 10-channel AS7341 optical band reflectance ($415\text{ nm} - 850\text{ nm}$ near-infrared).
- **Stream 2 (Spatial/RGB)**: 2D Convolutional encoder processing $(3, 64, 64)$ RGB canopy imagery patches.
- **Stream 3 (Environmental)**: MLP encoder for Temperature, Humidity, Soil Moisture, and Gas PPM metrics.
- **Cross-Attention Fusion Layer**: Cross-attention mechanism between Spectral & Spatial embeddings with Environmental feature vector concatenation.
- **Multi-Task Prediction Heads**:
  - 6-Class Condition Logits (`HEALTHY`, `PRE_SYMPTOMATIC_STRESS`, `WATER_STRESS`, `DISEASE`, `SEVERE_STRESS`, `UNKNOWN_ANOMALY`).
  - Softmax probability distribution.
  - Continuous severity score ($0 - 100$).
  - Empirical lead-time estimation in hours before symptomatic manifestation.

### 🔍 2. Explainable AI (XAI) & Out-Of-Distribution Anomaly Engine (`services/xai_service.py`)
- **Grad-CAM Heatmaps**: Spatial activation overlay maps highlighting diseased canopy zones.
- **AS7341 Band Importance Attribution**: Spectral feature attributions across $415\text{ nm} - 850\text{ nm}$ wavelengths.
- **Mahalanobis Distance OOD Detector**: Latent feature distance tracking to identify novel crop stresses or hardware sensor failures (`UNKNOWN_ANOMALY`).

### 🗺️ 3. Real Geospatial DBSCAN Hotspot & Bounding Area Engine (`services/geospatial_service.py`)
- Real-time density-based spatial clustering (`sklearn.cluster.DBSCAN`) grouping stress telemetry across field GPS coordinates.
- Computes cluster centroids, bounding polygon bounds, and exact affected field area in square meters ($m^2$).

### ✈️ 4. Autonomous UAV Mission Planner & Lawnmower Flight Paths (`services/mission_service.py`)
- **Lawnmower Survey Grid Generator**: Computes parallel survey flight paths over field boundary coordinates.
- **MAVLink / ArduPilot Hardware Abstraction**: Generates MAVLink 2.0 flight waypoints (`NAV_TAKEOFF`, `NAV_WAYPOINT`, `NAV_RETURN_TO_LAUNCH`).
- **AI-Driven Targeted Revisit Missions**: Automatically schedules low-altitude inspection hovers over high-severity DBSCAN hotspots.

### 💧 5. Closed-Loop Irrigation & Actuator Safety Guardrails (`services/irrigation_service.py`)
- Hardware relay actuation with mandatory 15-minute cooldown timers, maximum 300s duration caps, post-actuation moisture sampling verification, and instant Emergency Kill Switch override.

### 🧪 6. Software-In-The-Loop (SIL) Digital Twin Simulator (`services/digital_twin_service.py`)
- Multi-scenario field state injector (`HEALTHY_FIELD`, `WATER_STRESS_EPISODE`, `FUNGAL_DISEASE_OUTBREAK`, `SENSOR_DEGRADATION`, `GPS_LOSS`).

---

## 🚀 How to Launch the System Locally

### 📋 Prerequisites

1. **Python 3.10+**: Ensure Python is installed (`python --version`).
2. **PyTorch & Dependencies**: Installed via `requirements.txt` and `ml/requirements-ml.txt`.

---

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Akash-3/agrisense.git
cd agrisense
```

---

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
pip install -r ml/requirements-ml.txt
```

---

### 3️⃣ Train PyTorch MM-SSNet & Temporal Models (Optional)

```bash
python -m ml.train
python -m ml.ablation
```

Pre-trained model checkpoints are automatically saved to `ml/checkpoints/mmssnet.pth` and `ml/checkpoints/temporal_net.pth`. Ablation study results are stored in `ml/results/ablation_report.json`.

---

### 4️⃣ Launch the FastAPI Web Server

```bash
python app/run_app.py
```

Access the system locally at:
- 🌐 **Web Dashboard & Command Center**: [http://localhost:8000](http://localhost:8000)
- 📚 **AgriSense 2.0 Research Swagger APIs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 5️⃣ Run Automated Unit & E2E QA Test Suites

```bash
# Run PyTorch & Services Unit Tests
python -m unittest discover tests

# Run Virtual User Playwright E2E Browser QA Tests
python run_qa_tests.py
```

---

## 🔌 Unified ESP32 IoT Firmware Flashing

1. Open `esp32/unified_firmware/unified_firmware.ino` in Arduino IDE.
2. Copy `config.h.example` to `config.h` and configure Wi-Fi credentials (`WIFI_SSID`, `WIFI_PASSWORD`, `BACKEND_SERVER`).
3. Upload to ESP32 hardware board or flash pre-compiled binary via `esptool`.

---

## 📁 Repository Structure

```
agrisense/
├── app/                  # Web Application & FastAPI Backend
│   ├── backend/          # REST Endpoints, DB Engine, Routers (v2.py), & Services
│   │   └── services/     # AI, Fusion, Geospatial, XAI, UAV Mission, Irrigation, SIL Twin Services
│   ├── frontend/         # Command Center UI, Leaflet GIS Maps, & agrisense2.js
│   └── run_app.py        # Main Server Launcher Entry Point
├── ml/                   # Machine Learning Pipeline
│   ├── dataset.py        # Dataset DataLoader & Synthetic Generator
│   ├── model.py          # PyTorch MM-SSNet Model Architecture
│   ├── temporal.py       # GRU TemporalStressNet Model Architecture
│   ├── train.py          # Training Loop & Checkpoint Saver
│   ├── ablation.py       # Multimodal Stream Ablation Study
│   └── checkpoints/      # Trained PyTorch Model Weights (.pth)
├── esp32/                # Unified Production ESP32 Hardware Firmware
│   └── unified_firmware/ # Modular C++/Arduino Firmware & config.h template
├── tests/                # Automated Unit & Integration Tests
│   └── e2e/              # Playwright E2E Virtual User QA Tests
├── requirements.txt      # Root Python Dependencies
├── run_qa_tests.py       # E2E Test Suite Runner
└── README.md             # Platform Setup & Architecture Guide
```

---

## 🔒 License & Governance
Developed for the AgriSense 2.0 Autonomous Multimodal Agricultural Intelligence Platform.
