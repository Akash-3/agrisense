# AgriSense / AgriSense - SeaShark & Dart Native Application Guide

This repository contains the complete **SeaShark & Dart Native Cross-Platform Application** for the **AgriSense / AgriSense IoT Drone & AI Diagnostic Platform**.

It communicates with the FastAPI / C# backend via **real-time bi-directional WebSockets** (`ws://localhost:8000/ws/v1/telemetry`).

---

## 🏗️ Application Architecture

```
AgriSense Dart / SeaShark Application Structure
├── pubspec.yaml (Dart Dependencies: web_socket_channel, fl_chart, google_fonts)
└── lib/
    ├── main.dart (Glassmorphism Dashboard UI & FlChart 10-Channel Spectrum)
    ├── models/
    │   └── telemetry_models.dart (Dart PODO Models: AS7341 Optics, Soil VWC%, MM-SSNet AI)
    └── services/
        └── websocket_service.dart (Real-Time WebSocket Client Stream)
```

---

## ⚡ How to Run the Dart / SeaShark App

### Step 1: Ensure Backend WebSocket Server is Running
Make sure the Python FastAPI server is running on `http://localhost:8000`:

```bash
python C:\Users\tempm\.gemini\antigravity\scratch\agrisense\app\run_app.py
```

### Step 2: Launch the SeaShark / Dart App

Navigate to the project directory:

```bash
cd C:\Users\tempm\.gemini\antigravity\scratch\agrisense\seashark_dart_app
```

Get dependencies and run:

```bash
flutter pub get
flutter run -d windows   # To run as native Windows EXE
# OR
flutter run -d android   # To run on Android Phone / Emulator
```

---

## 📡 Live Telemetry & Simulation Control over WebSockets

1. **Automatic Streaming**:
   When launched, the SeaShark app automatically connects to `ws://localhost:8000/ws/v1/telemetry` and renders live 10-channel optical counts across F1 (415nm) to NIR (885nm).

2. **Interactive Examiner Demo Buttons**:
   Tap any preset button in the SeaShark toolbar to send immediate WebSocket commands to the server:
   * 🟢 **Healthy Crop**
   * 🟡 **Fungal Stress (5.4d Early Warning)**
   * 💧 **Soil Drought (<30% VWC Alert)**
   * 🔥 **Stubble Fire (>400 PPM Alert)**
