import os
import time
from typing import List
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends, Query, Header
from fastapi.responses import FileResponse, StreamingResponse
from dependencies import get_current_user
from simulator import TelemetryPayload, AIDiagnosticResult, simulator
from database import add_farm
from config import load_latest_app_version, get_existing_apk_path
from models.schemas import AddFarmRequest, ESP32TelemetryIngest

from app.backend.services import ai_service, fusion_service, anomaly_service

router = APIRouter(tags=["Telemetry & System"])

latest_telemetry: TelemetryPayload = simulator.generate_telemetry("HEALTHY")
latest_ai_result: dict = {
    "condition": "HEALTHY",
    "confidence": 0.96,
    "severity_score": 12.0,
    "estimated_lead_time_hours": 48.0,
    "is_real_ai": True,
    "model_version": "MM-SSNet-v2.0-PyTorch"
}
active_ws_clients: List[WebSocket] = []

@router.get("/api/v1/health")
async def health_check():
    ver_name, _ = load_latest_app_version()
    return {"status": "online", "service": "AgriSense Backend", "version": f"{ver_name}", "security": "PBKDF2 SHA-256 Shield Active"}

@router.get("/api/v1/update/check")
async def check_app_update(request: Request, current_version: str = "1.0.0"):
    latest_version, version_code = load_latest_app_version()
    has_update = (current_version != latest_version)
    host = request.headers.get("host") or str(request.url.netloc) or "localhost:8000"
    scheme = "https" if request.headers.get("x-forwarded-proto") == "https" else "http"
    download_url = f"{scheme}://{host}/api/v1/update/download"

    return {
        "has_update": has_update,
        "latest_version": latest_version,
        "version_code": version_code,
        "download_url": download_url,
        "release_notes": f"AgriSense v{latest_version} Release (Build {version_code}):\n• Real PyTorch MM-SSNet Telemetry Ingestion Pipeline\n• MobileNetV3 + AS7341 Multimodal AI Integration"
    }

@router.get("/api/v1/update/download")
async def download_apk_update(request: Request):
    apk_path = get_existing_apk_path()
    if not os.path.exists(apk_path):
        raise HTTPException(status_code=404, detail="APK Update file not found on server")

    file_size = os.path.getsize(apk_path)
    ver_name, _ = load_latest_app_version()
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
                        chunk_size = 1024 * 1024
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
                    "Content-Disposition": f'attachment; filename="AgriSense_v{ver_name}.apk"'
                }
                return StreamingResponse(iter_file(), status_code=206, headers=headers)
        except HTTPException:
            raise
        except Exception:
            pass

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": "application/vnd.android.package-archive",
        "Content-Disposition": f'attachment; filename="AgriSense_v{ver_name}.apk"'
    }
    return FileResponse(
        path=apk_path,
        filename=f"AgriSense_v{ver_name}.apk",
        media_type="application/vnd.android.package-archive",
        headers=headers
    )

@router.post("/api/v1/farms/add")
async def handle_add_farm(req: AddFarmRequest, current_user: int = Depends(get_current_user)):
    return add_farm(current_user, req.farm_name, req.farm_acres, req.crop_type)

@router.get("/api/v1/telemetry/latest")
async def get_latest_telemetry(current_user: int = Depends(get_current_user)):
    from database import get_farm_owner
    if latest_telemetry.farm_id is not None:
        owner = get_farm_owner(latest_telemetry.farm_id)
        if owner is not None and owner != current_user:
            raise HTTPException(status_code=403, detail="Forbidden")
    return {"telemetry": latest_telemetry.dict(), "ai_diagnosis": latest_ai_result}

@router.post("/api/v1/telemetry/ingest")
async def ingest_esp32_telemetry(payload: ESP32TelemetryIngest, request: Request = None, x_api_key: str = Header(None)):
    """
    REAL TELEMETRY INGESTION PIPELINE:
    ESP32 -> Ingest -> MM-SSNet (PyTorch) -> Fusion Service -> OOD Detection -> DB/Storage -> WebSocket -> Dashboard
    """
    if not x_api_key or x_api_key != os.environ.get("DEVICE_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")

    global latest_telemetry, latest_ai_result

    import json
    from database import execute_db
    # Device Resolution
    dev_row = execute_db("SELECT zone_id FROM devices WHERE device_id = ?", (payload.device_id,), fetchone=True)
    if not dev_row:
        raise HTTPException(status_code=404, detail="Device not provisioned")
    zone_id = dev_row[0]

    zone_row = execute_db("SELECT farm_id FROM zones WHERE id = ?", (zone_id,), fetchone=True)
    if not zone_row:
        raise HTTPException(status_code=403, detail="Zone not found")
    farm_id = zone_row[0]

    crop_row = execute_db("SELECT id, crop_name FROM crops WHERE zone_id = ? AND status = 'PLANTED' LIMIT 1", (zone_id,), fetchone=True)
    crop_id = crop_row[0] if crop_row else None
    crop_name = crop_row[1] if crop_row else None

    # 1. Telemetry Ingestion & Validation
    latest_telemetry.device_id = payload.device_id
    latest_telemetry.is_real_hardware = True

    latest_telemetry.soil_moisture_vwc = payload.soil_moisture
    latest_telemetry.temperature_c = payload.temperature
    latest_telemetry.humidity_pct = payload.humidity
    latest_telemetry.smoke_ppm = payload.smoke_ppm

    latest_telemetry.soil_status = payload.soil_status or ("ONLINE" if payload.soil_moisture is not None else "SENSOR_DISCONNECTED")
    latest_telemetry.dht_status = payload.dht_status or ("ONLINE" if payload.temperature is not None else "SENSOR_DISCONNECTED")
    latest_telemetry.mq135_status = payload.mq135_status or ("ONLINE" if payload.smoke_ppm is not None else "SENSOR_DISCONNECTED")
    latest_telemetry.timestamp = time.time()

    latest_telemetry.farm_id = farm_id

    # 2. Check for valid 10-band AS7341 spectral data
    raw_spectral = getattr(payload, "spectral", None)
    if raw_spectral is None and request is not None:
        try:
            body = await request.json()
            if isinstance(body, dict):
                raw_spectral = body.get("spectral")
        except Exception:
            pass

    has_valid_spectral = isinstance(raw_spectral, (list, tuple)) and len(raw_spectral) == 10

    if has_valid_spectral:
        spectral_arr = list(raw_spectral)
        env_arr = [
            payload.temperature,
            payload.humidity,
            payload.soil_moisture,
            payload.smoke_ppm
        ]
        # 3. PyTorch MM-SSNet Real Forward Pass
        ai_pred = ai_service.predict(spectral_arr, env_arr)

        # 4. Sensor Fusion Disambiguation
        fused_diag = fusion_service.disambiguate_stress(ai_pred, {
            "temperature": payload.temperature,
            "humidity": payload.humidity,
            "soil_moisture": payload.soil_moisture,
            "smoke_ppm": payload.smoke_ppm
        })

        # 5. OOD Anomaly Evaluation
        ood_eval = anomaly_service.evaluate_ood(ai_pred["latent_features"], spectral_arr, env_arr)

        latest_ai_result = {
            "condition": fused_diag["final_condition"],
            "confidence": fused_diag["disambiguated_confidence"],
            "severity_score": fused_diag["severity_score"],
            "estimated_lead_time_hours": ai_pred["estimated_lead_time_hours"],
            "probabilities": ai_pred["probabilities"],
            "reasoning_trace": fused_diag["reasoning_trace"],
            "recommended_action": fused_diag["recommended_action"],
            "rule_type": fused_diag["rule_type"],
            "is_anomaly": ood_eval.get("is_anomaly", False),
            "is_real_ai": True,
            "pipeline": "REAL_ESP32 -> PYTORCH_MMSSNET -> FUSION -> OOD -> WEBSOCKET",
            "model_version": "MM-SSNet-v2.0-PyTorch"
        }

        db_spectral = json.dumps(spectral_arr)
        db_ai_condition = fused_diag["final_condition"]
        db_ai_confidence = fused_diag["disambiguated_confidence"]
        db_ai_severity = fused_diag["severity_score"]
        db_ai_rule_type = fused_diag["rule_type"]
        db_ai_action = fused_diag["recommended_action"]
        db_anomaly_score = ood_eval.get("ood_score", 0.0)
        db_ood_score = ood_eval.get("ood_score", 0.0)
    else:
        spectral_arr = None
        ood_eval = {}
        latest_ai_result = {
            "condition": None,
            "confidence": None,
            "severity_score": None,
            "estimated_lead_time_hours": None,
            "probabilities": None,
            "reasoning_trace": ["AI diagnosis unavailable: Spectral data absent or incomplete."],
            "recommended_action": None,
            "rule_type": None,
            "is_anomaly": False,
            "is_real_ai": False,
            "pipeline": "NO_SPECTRAL_DATA",
            "model_version": "MM-SSNet-v2.0-PyTorch"
        }

        db_spectral = None
        db_ai_condition = None
        db_ai_confidence = None
        db_ai_severity = None
        db_ai_rule_type = None
        db_ai_action = None
        db_anomaly_score = None
        db_ood_score = None

    execute_db(
        "INSERT INTO telemetry_records (device_id, zone_id, farm_id, crop_id, crop_name, timestamp, soil_moisture, temperature, humidity, smoke_ppm, spectral_data, ai_condition, ai_confidence, ai_severity, ai_rule_type, ai_recommended_action, anomaly_score, ood_score, is_simulated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (payload.device_id, zone_id, farm_id, crop_id, crop_name, latest_telemetry.timestamp, payload.soil_moisture, payload.temperature, payload.humidity, payload.smoke_ppm, db_spectral, db_ai_condition, db_ai_confidence, db_ai_severity, db_ai_rule_type, db_ai_action, db_anomaly_score, db_ood_score, False),
        commit=True
    )

    await broadcast_websocket_telemetry()

    return {
        "status": "success",
        "pipeline": "REAL_TELEMETRY_PIPELINE",
        "message": f"ESP32 Telemetry from '{payload.device_id}' processed with PyTorch MM-SSNet!",
        "device_id": payload.device_id,
        "zone_id": zone_id,
        "farm_id": farm_id,
        "crop_name": crop_name,
        "received_data": {
            "soil_moisture_pct": payload.soil_moisture,
            "temperature_c": payload.temperature,
            "humidity_pct": payload.humidity,
            "smoke_ppm": payload.smoke_ppm,
        },
        "ai_diagnosis": latest_ai_result,
        "anomaly_analysis": ood_eval,
        "timestamp": latest_telemetry.timestamp
    }

@router.post("/api/v1/simulate")
async def trigger_simulation_preset(preset: str = "HEALTHY", current_user: int = Depends(get_current_user)):
    """
    Explicit SIL Simulation Preset Route (Explicitly Tagged as Simulation Mode).
    """
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

    from database import execute_db
    # Find any farm for the user to tie the simulation to
    farm_row = execute_db("SELECT id FROM farms WHERE farmer_id = ? LIMIT 1", (current_user,), fetchone=True)
    sim_farm_id = farm_row[0] if farm_row else 1
    zone_row = execute_db("SELECT id FROM zones WHERE farm_id = ? LIMIT 1", (sim_farm_id,), fetchone=True)
    sim_zone_id = zone_row[0] if zone_row else 1

    latest_telemetry = simulator.generate_telemetry(preset_key)
    latest_telemetry.is_real_hardware = False
    latest_telemetry.farm_id = sim_farm_id

    # Run PyTorch AI prediction on simulated preset
    env_arr = [latest_telemetry.temperature_c, latest_telemetry.humidity_pct, latest_telemetry.soil_moisture_vwc, latest_telemetry.smoke_ppm]
    spec_arr = [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]
    ai_pred = ai_service.predict(spec_arr, env_arr)

    latest_ai_result = {
        "condition": ai_pred["condition"],
        "confidence": ai_pred["confidence"],
        "severity_score": ai_pred["severity_score"],
        "estimated_lead_time_hours": ai_pred["estimated_lead_time_hours"],
        "is_real_ai": True,
        "pipeline": "SIL_SIMULATION_MODE",
        "model_version": "MM-SSNet-v2.0-PyTorch"
    }

    import json
    execute_db(
        "INSERT INTO telemetry_records (device_id, zone_id, farm_id, crop_id, crop_name, timestamp, soil_moisture, temperature, humidity, smoke_ppm, spectral_data, ai_condition, ai_confidence, ai_severity, ai_rule_type, ai_recommended_action, anomaly_score, ood_score, is_simulated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (latest_telemetry.device_id, sim_zone_id, sim_farm_id, None, None, latest_telemetry.timestamp, latest_telemetry.soil_moisture_vwc, latest_telemetry.temperature_c, latest_telemetry.humidity_pct, latest_telemetry.smoke_ppm, json.dumps(spec_arr), ai_pred["condition"], ai_pred["confidence"], ai_pred["severity_score"], None, None, 0.0, 0.0, True),
        commit=True
    )

    await broadcast_websocket_telemetry()
    return {
        "mode": "SIMULATION",
        "preset_applied": preset,
        "telemetry": latest_telemetry.dict(),
        "ai_diagnosis": latest_ai_result
    }

    await broadcast_websocket_telemetry()
    return {
        "mode": "SIMULATION",
        "preset_applied": preset,
        "telemetry": latest_telemetry.dict(),
        "ai_diagnosis": latest_ai_result
    }

@router.websocket("/ws/v1/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket, token: str = Query(...)):
    from database import execute_db, get_farm_owner
    row = execute_db("SELECT farmer_id, expires_at FROM auth_sessions WHERE session_token = ?", (token,), fetchone=True)
    if not row or time.time() > row[1]:
        await websocket.close(code=1008)
        return

    current_user = row[0]
    await websocket.accept()

    # Store farmer_id on the websocket object
    websocket.farmer_id = current_user
    active_ws_clients.append(websocket)

    try:
        if latest_telemetry.farm_id is not None:
            owner = get_farm_owner(latest_telemetry.farm_id)
            if owner == current_user:
                initial_data = {
                    "telemetry": latest_telemetry.dict(),
                    "ai_diagnosis": latest_ai_result
                }
                await websocket.send_json(initial_data)

        while True:
            msg = await websocket.receive_json()
            if msg.get("action") == "simulate":
                await trigger_simulation_preset(msg.get("preset", "HEALTHY"), current_user=current_user)
    except WebSocketDisconnect:
        if websocket in active_ws_clients:
            active_ws_clients.remove(websocket)
    except Exception:
        if websocket in active_ws_clients:
            active_ws_clients.remove(websocket)

async def broadcast_websocket_telemetry():
    from database import get_farm_owner
    if not active_ws_clients:
        return

    data = {
        "telemetry": latest_telemetry.dict(),
        "ai_diagnosis": latest_ai_result
    }

    # Check owner of latest_telemetry
    farm_id = latest_telemetry.farm_id
    owner = get_farm_owner(farm_id) if farm_id is not None else None

    for client in list(active_ws_clients):
        try:
            if owner is None or getattr(client, 'farmer_id', None) == owner:
                await client.send_json(data)
        except Exception:
            if client in active_ws_clients:
                active_ws_clients.remove(client)


@router.get("/api/v1/telemetry/history")
async def get_historical_telemetry(
    farm_id: int,
    zone_id: int = None,
    crop_id: int = None,
    device_id: str = None,
    limit: int = 50,
    current_user: int = Depends(get_current_user)
):
    from database import get_farm_owner, get_zone_owner, get_crop_owner, get_device_by_device_id, execute_db

    farm_owner = get_farm_owner(farm_id)
    if farm_owner is None or farm_owner != current_user:
        raise HTTPException(status_code=403, detail="Forbidden: Not your farm")

    if zone_id is not None:
        zone_owner = get_zone_owner(zone_id)
        if zone_owner is None or zone_owner != current_user:
            raise HTTPException(status_code=403, detail="Forbidden: Not your zone")

    if crop_id is not None:
        crop_owner = get_crop_owner(crop_id)
        if crop_owner is None or crop_owner != current_user:
            raise HTTPException(status_code=403, detail="Forbidden: Not your crop")

    if device_id is not None:
        device = get_device_by_device_id(device_id)
        if device is not None:
            dev_zone_owner = get_zone_owner(device["zone_id"])
            if dev_zone_owner is None or dev_zone_owner != current_user:
                raise HTTPException(status_code=403, detail="Forbidden: Not your device")

    query = "SELECT * FROM telemetry_records WHERE farm_id = ?"
    params = [farm_id]

    if zone_id is not None:
        query += " AND zone_id = ?"
        params.append(zone_id)
    if crop_id is not None:
        query += " AND crop_id = ?"
        params.append(crop_id)
    if device_id is not None:
        query += " AND device_id = ?"
        params.append(device_id)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = execute_db(query, tuple(params), fetchall=True)
    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "device_id": row[1],
            "zone_id": row[2],
            "farm_id": row[3],
            "crop_id": row[4],
            "crop_name": row[5],
            "timestamp": row[6],
            "soil_moisture": row[7],
            "temperature": row[8],
            "humidity": row[9],
            "smoke_ppm": row[10],
            "spectral_data": row[11],
            "ai_condition": row[12],
            "ai_confidence": row[13],
            "ai_severity": row[14],
            "ai_rule_type": row[15],
            "ai_recommended_action": row[16],
            "anomaly_score": row[17],
            "ood_score": row[18],
            "is_simulated": bool(row[19]) if row[19] is not None else False
        })
    return {"history": history}
