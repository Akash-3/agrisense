from fastapi import APIRouter, HTTPException, Query, Depends
from dependencies import get_current_user
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any

from app.backend.services import (
    ai_service,
    temporal_service,
    fusion_service,
    anomaly_service,
    geospatial_service,
    xai_service,
    mission_service,
    irrigation_service,
    digital_twin_service
)

router = APIRouter(prefix="/api/v2", tags=["AgriSense 2.0 Research APIs"])

# --- Request Models ---
class PredictRequest(BaseModel):
    spectral: List[float]
    temperature: float
    humidity: float
    soil_moisture: float
    smoke_ppm: float
    spatial: Optional[List[List[List[float]]]] = None

class XAIRequest(BaseModel):
    spectral: List[float]
    spatial_img: Optional[List[List[List[float]]]] = None
    condition: Optional[str] = None

class TemporalRequest(BaseModel):
    historical_sequence: List[List[float]]

class AnomalyRequest(BaseModel):
    latent_features: List[float]
    spectral: Optional[List[float]] = None
    env: Optional[List[float]] = None

class ActuationRequest(BaseModel):
    zone_id: str = "ZONE-A"
    duration_sec: int = 60
    trigger_source: Optional[str] = "AI_CLOSED_LOOP"

class LawnmowerMissionRequest(BaseModel):
    boundary_coords: List[Dict[str, float]]
    altitude_m: Optional[float] = 15.0
    spacing_m: Optional[float] = 10.0

    @validator('boundary_coords')
    def validate_boundary(cls, v):
        if len(v) > 200:
            raise ValueError('Maximum polygon vertex limit is 200')
        import math
        min_lat, max_lat, min_lng, max_lng = 90.0, -90.0, 180.0, -180.0
        for coord in v:
            if 'lat' not in coord or 'lng' not in coord:
                raise ValueError('required coordinate keys missing')
            lat, lng = coord['lat'], coord['lng']
            if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                raise ValueError('reject malformed coordinates')
            if math.isnan(lat) or math.isnan(lng):
                raise ValueError('reject NaN')
            if math.isinf(lat) or math.isinf(lng):
                raise ValueError('reject infinity')
            if not (-90 <= lat <= 90):
                raise ValueError('latitude [-90, 90]')
            if not (-180 <= lng <= 180):
                raise ValueError('longitude [-180, 180]')
            min_lat = min(min_lat, lat)
            max_lat = max(max_lat, lat)
            min_lng = min(min_lng, lng)
            max_lng = max(max_lng, lng)
        if len(v) > 0 and ((max_lat - min_lat) > 0.5 or (max_lng - min_lng) > 0.5):
            raise ValueError('existing 0.5-degree boundary constraint')
        return v

    @validator('spacing_m')
    def validate_spacing(cls, v):
        if v is not None and (v < 1.0 or v > 1000.0):
            raise ValueError('spacing_m >= 1.0 and <= 1000.0')
        return v

    @validator('altitude_m')
    def validate_altitude(cls, v):
        if v is not None and v < 0:
            raise ValueError('altitude >= 0')
        return v

class RevisitMissionRequest(BaseModel):
    hotspot_id: str = "HS-DB-01"
    centroid: Dict[str, float]

    @validator('centroid')
    def validate_centroid(cls, v):
        import math
        if 'lat' not in v or 'lng' not in v:
            raise ValueError('required coordinate keys missing')
        lat, lng = v['lat'], v['lng']
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            raise ValueError('reject malformed coordinates')
        if math.isnan(lat) or math.isnan(lng):
            raise ValueError('reject NaN')
        if math.isinf(lat) or math.isinf(lng):
            raise ValueError('reject infinity')
        if not (-90 <= lat <= 90):
            raise ValueError('latitude [-90, 90]')
        if not (-180 <= lng <= 180):
            raise ValueError('longitude [-180, 180]')
        return v

class SetScenarioRequest(BaseModel):
    scenario_name: str

# --- Endpoints ---

@router.post("/ai/predict")
def predict_multimodal(req: PredictRequest, current_user: int = Depends(get_current_user)):
    """
    Runs PyTorch MM-SSNet (MobileNetV3 spatial stream) forward pass and applies physical sensor fusion.
    """
    if len(req.spectral) != 10:
        raise HTTPException(status_code=400, detail="Spectral vector must contain exactly 10 AS7341 channels.")

    env_vec = [req.temperature, req.humidity, req.soil_moisture, req.smoke_ppm]
    
    # 1. MM-SSNet PyTorch Forward Pass
    raw_ai_res = ai_service.predict(req.spectral, env_vec, req.spatial)

    # 2. Physical Fusion Disambiguation
    telemetry_dict = {
        "temperature": req.temperature,
        "humidity": req.humidity,
        "soil_moisture": req.soil_moisture,
        "smoke_ppm": req.smoke_ppm
    }
    fused_res = fusion_service.disambiguate_stress(raw_ai_res, telemetry_dict)

    # 3. Calibrated OOD Anomaly Evaluation
    try:
        ood_res = anomaly_service.evaluate_ood(raw_ai_res["latent_features"], req.spectral, env_vec)
    except ValueError as ve:
        ood_res = {"is_calibrated": False, "error": str(ve)}

    return {
        "status": "SUCCESS",
        "model_architecture": "PyTorch MM-SSNet (MobileNetV3 + 1D-Conv AS7341 + Env MLP)",
        "ai_prediction": raw_ai_res,
        "fused_diagnosis": fused_res,
        "anomaly_analysis": ood_res
    }

@router.post("/ai/xai")
def get_xai_explanation(req: XAIRequest, current_user: int = Depends(get_current_user)):
    """
    Generates PyTorch Grad-CAM visual heatmaps (MobileNetV3) and Input x Gradient spectral attributions.
    """
    res = xai_service.generate_xai_explanation(req.spectral, req.spatial_img)
    return {"status": "SUCCESS", "xai_explanation": res}

@router.post("/ai/temporal-trend")
def evaluate_temporal_trend(req: TemporalRequest, current_user: int = Depends(get_current_user)):
    """
    Evaluates historical telemetry sequence using PyTorch GRU TemporalStressNet.
    """
    res = temporal_service.evaluate_trend(req.historical_sequence)
    return {"status": "SUCCESS", "temporal_trend": res}

@router.post("/ai/anomaly")
def evaluate_anomaly(req: AnomalyRequest, current_user: int = Depends(get_current_user)):
    """
    Out-Of-Distribution (OOD) evaluation using fitted Mahalanobis detector calibration parameters.
    """
    try:
        res = anomaly_service.evaluate_ood(req.latent_features, req.spectral, req.env)
        return {"status": "SUCCESS", "anomaly_evaluation": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/spatial/hotspots")
def get_spatial_hotspots(telemetry_nodes: Optional[List[Dict[str, Any]]] = None, eps_meters: float = 20.0, min_samples: int = 2, current_user: int = Depends(get_current_user)):
    """
    Runs DBSCAN spatial clustering on provided or stored field node telemetry.
    Strictly reports estimated bounding area (m²).
    """
    nodes = telemetry_nodes or []
    res = geospatial_service.cluster_hotspots(nodes, eps_meters=eps_meters, min_samples=min_samples)
    return {"status": "SUCCESS", "spatial_clusters": res}

@router.get("/spatial/hotspots/simulation")
def get_simulated_hotspots(current_user: int = Depends(get_current_user)):
    """
    Development & SIL Simulation endpoint for testing DBSCAN spatial clustering with sample field nodes.
    """
    sample_nodes = [
        {"node_id": "NODE-01", "lat": 28.6139, "lng": 77.2090, "severity": 65.0, "condition": "WATER_STRESS"},
        {"node_id": "NODE-02", "lat": 28.6140, "lng": 77.2091, "severity": 70.0, "condition": "WATER_STRESS"},
        {"node_id": "NODE-03", "lat": 28.6138, "lng": 77.2089, "severity": 62.0, "condition": "WATER_STRESS"},
        {"node_id": "NODE-05", "lat": 28.6180, "lng": 77.2130, "severity": 82.0, "condition": "DISEASE"},
        {"node_id": "NODE-06", "lat": 28.6181, "lng": 77.2131, "severity": 85.0, "condition": "DISEASE"}
    ]
    res = geospatial_service.cluster_hotspots(sample_nodes, eps_meters=20.0, min_samples=2)
    return {"status": "SUCCESS", "mode": "SIMULATION", "spatial_clusters": res}

@router.post("/uav/mission/generate")
def generate_uav_mission(req: LawnmowerMissionRequest, current_user: int = Depends(get_current_user)):
    """
    Generates Lawnmower flight survey mission. Rejects request if field boundary coordinates are missing.
    """
    try:
        res = mission_service.generate_lawnmower_pattern(req.boundary_coords, req.altitude_m, req.spacing_m)
        return {"status": "SUCCESS", "uav_mission": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/uav/mission/targeted-revisit")
def generate_targeted_revisit(req: RevisitMissionRequest, current_user: int = Depends(get_current_user)):
    """
    Generates targeted revisit flight mission for DBSCAN hotspots.
    """
    try:
        hotspot_dict = {"hotspot_id": req.hotspot_id, "centroid": req.centroid}
        res = mission_service.plan_targeted_revisit(hotspot_dict)
        return {"status": "SUCCESS", "revisit_mission": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/actuators/trigger")
def trigger_actuator(req: ActuationRequest, current_user: int = Depends(get_current_user)):
    """
    Triggers relay actuation through pluggable RelayAdapter interface.
    """
    from database import get_zone_owner, get_device_by_device_id

    zone_id = None
    if str(req.zone_id).isdigit():
        zone_id = int(req.zone_id)
    else:
        device = get_device_by_device_id(str(req.zone_id))
        if device is not None:
            zone_id = device["zone_id"]
        else:
            raise HTTPException(status_code=400, detail="Unknown symbolic zone or device identifier")

    if zone_id is None:
        raise HTTPException(status_code=400, detail="Malformed identifier")

    owner_id = get_zone_owner(zone_id)
    if owner_id is None or owner_id != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")

    res = irrigation_service.trigger_actuator(req.zone_id, req.duration_sec, req.trigger_source)
    return {"status": "SUCCESS", "actuator_response": res}

@router.post("/actuators/emergency-stop")
def emergency_stop(current_user: int = Depends(get_current_user)):
    res = irrigation_service.emergency_stop()
    return {"status": "SUCCESS", "emergency_stop": res}

@router.post("/actuators/reset-emergency-stop")
def reset_emergency_stop(current_user: int = Depends(get_current_user)):
    res = irrigation_service.reset_emergency_stop()
    return {"status": "SUCCESS", "emergency_stop": res}

@router.get("/actuators/status")
def get_actuator_status(current_user: int = Depends(get_current_user)):
    res = irrigation_service.get_status()
    return {"status": "SUCCESS", "actuator_status": res}

@router.post("/simulation/digital-twin/set-scenario")
def set_digital_twin_scenario(req: SetScenarioRequest, current_user: int = Depends(get_current_user)):
    res = digital_twin_service.set_scenario(req.scenario_name, user_id=current_user)
    return {"status": "SUCCESS", "digital_twin": res}

@router.get("/simulation/digital-twin/telemetry")
def get_digital_twin_telemetry(node_id: str = "NODE-01", current_user: int = Depends(get_current_user)):
    res = digital_twin_service.generate_simulated_telemetry(node_id, user_id=current_user)
    return {"status": "SUCCESS", "simulated_telemetry": res}
