import os
import time
from typing import List
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from simulator import TelemetryPayload, AIDiagnosticResult, simulator
from database import add_farm
from config import load_latest_app_version, get_existing_apk_path, LATEST_APP_VERSION
from models.schemas import AddFarmRequest, ESP32TelemetryIngest

router = APIRouter(tags=["Telemetry & System"])

latest_telemetry: TelemetryPayload = simulator.generate_telemetry("HEALTHY")
latest_ai_result: AIDiagnosticResult = simulator.compute_mm_ssnet_inference(latest_telemetry)
active_ws_clients: List[WebSocket] = []

@router.get("/api/v1/health")
async def health_check():
    return {"status": "online", "service": "AgriSense Backend", "version": f"{LATEST_APP_VERSION}", "security": "PBKDF2 SHA-256 Shield Active"}

@router.get("/api/v1/update/check")
async def check_app_update(request: Request, current_version: str = "1.0.0"):
    latest_version, version_code = load_latest_app_version()
    has_update = (current_version != latest_version)
    host = request.headers.get("host") or str(request.url.netloc) or "localhost:8000"
    scheme = "https" if ("trycloudflare.com" in host or request.headers.get("x-forwarded-proto") == "https") else "http"
    download_url = f"{scheme}://{host}/api/v1/update/download"
        
    return {
        "has_update": has_update,
        "latest_version": latest_version,
        "version_code": version_code,
        "download_url": download_url,
        "release_notes": f"AgriSense v{latest_version} Release (Build {version_code}):\n• Single Source of Truth Dynamic Versioning & Synchronized Build Engine\n• Solved version mismatch between OTA download and installed app UI\n• Automatic Android Gradle VersionCode & VersionName Alignment"
    }

@router.get("/api/v1/update/download")
async def download_apk_update(request: Request):
    apk_path = get_existing_apk_path()
    if not os.path.exists(apk_path):
        raise HTTPException(status_code=404, detail="APK Update file not found on server")

    file_size = os.path.getsize(apk_path)
    print(f"[OTA DOWNLOAD ENGINE] Serving package '{apk_path}' ({file_size} bytes) for v{LATEST_APP_VERSION}")
    range_header = request.headers.get("range")

    if range_header:
        try:
            unit, range_val = range_header.strip().split("=")
            if unit == "bytes":
                start_str, end_str = range_val.split("-")
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1

                if start >= file_size:
                    raise HTTPException(status_code=416, detail="Requested Range Not Satisfiable")

                end = min(end, file_size - 1)
                content_length = (end - start) + 1

                def iter_file():
                    with open(apk_path, "rb") as f:
                        f.seek(start)
                        remaining = content_length
                        chunk_size = 1024 * 1024  # 1MB chunk size for high-throughput 5G/Wi-Fi streaming
                        while remaining > 0:
                            read_bytes = min(remaining, chunk_size)
                            data = f.read(read_bytes)
                            if not data:
                                break
                            remaining -= len(data)
                            yield data

                headers = {
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(content_length),
                    "Content-Type": "application/vnd.android.package-archive",
                    "Content-Disposition": f'attachment; filename="AgriSense_v{LATEST_APP_VERSION}.apk"'
                }
                return StreamingResponse(iter_file(), status_code=206, headers=headers)
        except HTTPException:
            raise
        except Exception as e:
            print(f"[RANGE PARSE ERROR] {e}")

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": "application/vnd.android.package-archive",
        "Content-Disposition": f'attachment; filename="AgriSense_v{LATEST_APP_VERSION}.apk"'
    }
    return FileResponse(
        path=apk_path,
        filename=f"AgriSense_v{LATEST_APP_VERSION}.apk",
        media_type="application/vnd.android.package-archive",
        headers=headers
    )

@router.post("/api/v1/farms/add")
async def handle_add_farm(req: AddFarmRequest):
    return add_farm(req.farmer_id, req.farm_name, req.farm_acres, req.crop_type)

@router.get("/api/v1/telemetry/latest")
async def get_latest_telemetry():
    return {"telemetry": latest_telemetry.dict(), "ai_diagnosis": latest_ai_result.dict()}

@router.post("/api/v1/telemetry/ingest")
async def ingest_esp32_telemetry(payload: ESP32TelemetryIngest):
    global latest_telemetry, latest_ai_result
    
    latest_telemetry.device_id = payload.device_id
    latest_telemetry.soil_moisture_vwc = max(0.0, min(100.0, payload.soil_moisture))
    latest_telemetry.temperature_c = payload.temperature
    latest_telemetry.humidity_pct = max(0.0, min(100.0, payload.humidity))
    latest_telemetry.smoke_ppm = max(0.0, payload.smoke_ppm)
    latest_telemetry.timestamp = time.time()
    
    latest_ai_result = simulator.compute_mm_ssnet_inference(latest_telemetry)
    await broadcast_websocket_telemetry()
    
    return {
        "status": "success",
        "message": f"ESP32 Soil Sensor Telemetry from '{payload.device_id}' ingested successfully!",
        "device_id": payload.device_id,
        "received_data": {
            "soil_moisture_pct": payload.soil_moisture,
            "temperature_c": payload.temperature,
            "humidity_pct": payload.humidity,
            "smoke_ppm": payload.smoke_ppm,
        },
        "ai_diagnosis": latest_ai_result.dict(),
        "timestamp": latest_telemetry.timestamp
    }

@router.post("/api/v1/simulate")
async def trigger_simulation_preset(preset: str = "HEALTHY"):
    global latest_telemetry, latest_ai_result
    preset_map = {
        "optimal": "HEALTHY",
        "water_stress": "PRE_SYMPTOMATIC_STRESS",
        "pest_outbreak": "SEVERE_DROUGHT",
        "nutrient_deficiency": "PRE_SYMPTOMATIC_STRESS",
        "disease_rust": "SMOKE_HAZARD",
    }
    preset_key = preset_map.get(preset, preset)
    if preset_key not in ["HEALTHY", "PRE_SYMPTOMATIC_STRESS", "SEVERE_DROUGHT", "SMOKE_HAZARD"]:
        raise HTTPException(status_code=400, detail="Invalid preset")
        
    latest_telemetry = simulator.generate_telemetry(preset_key)
    latest_ai_result = simulator.compute_mm_ssnet_inference(latest_telemetry)
    await broadcast_websocket_telemetry()
    return {
        "preset_applied": preset,
        "telemetry": latest_telemetry.dict(),
        "ai_diagnosis": latest_ai_result.dict()
    }

@router.websocket("/ws/v1/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    await websocket.accept()
    active_ws_clients.append(websocket)
    try:
        initial_data = {
            "telemetry": latest_telemetry.dict(),
            "ai_diagnosis": latest_ai_result.dict()
        }
        await websocket.send_json(initial_data)
        while True:
            msg = await websocket.receive_json()
            if msg.get("action") == "simulate":
                await trigger_simulation_preset(msg.get("preset", "HEALTHY"))
    except WebSocketDisconnect:
        if websocket in active_ws_clients:
            active_ws_clients.remove(websocket)
    except Exception:
        if websocket in active_ws_clients:
            active_ws_clients.remove(websocket)

async def broadcast_websocket_telemetry():
    if not active_ws_clients:
        return
    data = {
        "telemetry": latest_telemetry.dict(),
        "ai_diagnosis": latest_ai_result.dict()
    }
    for client in list(active_ws_clients):
        try:
            await client.send_json(data)
        except Exception:
            if client in active_ws_clients:
                active_ws_clients.remove(client)
