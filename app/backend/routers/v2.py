from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

try:
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
except ModuleNotFoundError:
    from services import (
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
    spectral: List[float] # 10 channels
    temperature: float
    humidity: float
    soil_moisture: float
    smoke_ppm: float
    spatial: Optional[List[List[List[float]]]] = None # (3, 64, 64)

class XAIRequest(BaseModel):
    spectral: List[float]
    condition: Optional[str] = "WATER_STRESS"

class TemporalRequest(BaseModel):
    historical_sequence: List[List[float]]

class AnomalyRequest(BaseModel):
    latent_features: Optional[List[float]] = None
    spectral: Optional[List[float]] = None
    env: Optional[List[float]] = None

class ActuationRequest(BaseModel):
    zone_id: str = "ZONE-A"
    duration_sec: int = 60
    trigger_source: Optional[str] = "AI_CLOSED_LOOP"

class LawnmowerMissionRequest(BaseModel):
    boundary_coords: Optional[List[Dict[str, float]]] = None
    altitude_m: Optional[float] = 15.0
    spacing_m: Optional[float] = 10.0

class RevisitMissionRequest(BaseModel):
    hotspot_id: str = "HS-DB-01"
    centroid: Dict[str, float] = {"lat": 28.6139, "lng": 77.2090}

class SetScenarioRequest(BaseModel):
    scenario_name: str

# --- Endpoints ---

@router.post("/ai/predict")
def predict_multimodal(req: PredictRequest):
    """
    Runs PyTorch MM-SSNet multi-modal forward pass and applies physical sensor fusion disambiguation.
    """
    if len(req.spectral) != 10:
        raise HTTPException(status_code=400, detail="Spectral vector must contain exactly 10 AS7341 channels.")

    env_vec = [req.temperature, req.humidity, req.soil_moisture, req.smoke_ppm]
    
    # 1. MM-SSNet PyTorch Prediction
    raw_ai_res = ai_service.predict(req.spectral, env_vec, req.spatial)

    # 2. Sensor Fusion & Physical Rules Disambiguation
    telemetry_dict = {
        "temperature": req.temperature,
        "humidity": req.humidity,
        "soil_moisture": req.soil_moisture,
        "smoke_ppm": req.smoke_ppm
    }
    fused_res = fusion_service.disambiguate_stress(raw_ai_res, telemetry_dict)

    # 3. OOD Anomaly Evaluation
    ood_res = anomaly_service.evaluate_ood(raw_ai_res["latent_features"], req.spectral, env_vec)

    return {
        "status": "SUCCESS",
        "ai_prediction": raw_ai_res,
        "fused_diagnosis": fused_res,
        "anomaly_analysis": ood_res
    }

@router.post("/ai/xai")
def get_xai_explanation(req: XAIRequest):
    """
    Generates Grad-CAM visual heatmap overlay matrix and AS7341 spectral band attributions.
    """
    res = xai_service.generate_xai_explanation(req.spectral, req.condition)
    return {"status": "SUCCESS", "xai_explanation": res}

@router.post("/ai/temporal-trend")
def evaluate_temporal_trend(req: TemporalRequest):
    """
    Evaluates multi-timestep historical sequences using PyTorch GRU TemporalStressNet.
    """
    res = temporal_service.evaluate_trend(req.historical_sequence)
    return {"status": "SUCCESS", "temporal_trend": res}

@router.post("/ai/anomaly")
def evaluate_anomaly(req: AnomalyRequest):
    """
    Out-Of-Distribution (OOD) and hardware fault evaluation.
    """
    res = anomaly_service.evaluate_ood(req.latent_features, req.spectral, req.env)
    return {"status": "SUCCESS", "anomaly_evaluation": res}

@router.get("/spatial/hotspots")
def get_spatial_hotspots(eps_meters: float = 20.0, min_samples: int = 2):
    """
    Runs DBSCAN density-based spatial clustering across field nodes and computes bounding polygons ($m^2$).
    """
    # Sample field telemetry nodes across farm coordinates
    sample_nodes = [
        {"node_id": "NODE-01", "lat": 28.6139, "lng": 77.2090, "severity": 65.0, "condition": "WATER_STRESS"},
        {"node_id": "NODE-02", "lat": 28.6140, "lng": 77.2091, "severity": 70.0, "condition": "WATER_STRESS"},
        {"node_id": "NODE-03", "lat": 28.6138, "lng": 77.2089, "severity": 62.0, "condition": "WATER_STRESS"},
        {"node_id": "NODE-04", "lat": 28.6160, "lng": 77.2110, "severity": 10.0, "condition": "HEALTHY"},
        {"node_id": "NODE-05", "lat": 28.6180, "lng": 77.2130, "severity": 82.0, "condition": "DISEASE"},
        {"node_id": "NODE-06", "lat": 28.6181, "lng": 77.2131, "severity": 85.0, "condition": "DISEASE"}
    ]

    res = geospatial_service.cluster_hotspots(sample_nodes, eps_meters=eps_meters, min_samples=min_samples)
    return {"status": "SUCCESS", "spatial_clusters": res}

@router.post("/uav/mission/generate")
def generate_uav_mission(req: LawnmowerMissionRequest):
    """
    Generates Lawnmower flight survey mission with MAVLink waypoints.
    """
    res = mission_service.generate_lawnmower_pattern(req.boundary_coords, req.altitude_m, req.spacing_m)
    return {"status": "SUCCESS", "uav_mission": res}

@router.post("/uav/mission/targeted-revisit")
def generate_targeted_revisit(req: RevisitMissionRequest):
    """
    Generates AI-triggered low-altitude targeted revisit flight mission.
    """
    hotspot_dict = {"hotspot_id": req.hotspot_id, "centroid": req.centroid}
    res = mission_service.plan_targeted_revisit(hotspot_dict)
    return {"status": "SUCCESS", "revisit_mission": res}

@router.post("/actuators/control")
def trigger_actuator(req: ActuationRequest):
    """
    Triggers pump/valve relay actuation after verifying safety limits and cooldown timers.
    """
    res = irrigation_service.trigger_actuator(req.zone_id, req.duration_sec, req.trigger_source)
    return {"status": "SUCCESS", "actuator_response": res}

@router.post("/actuators/emergency-stop")
def emergency_stop():
    """
    Activates immediate emergency kill switch cutting all relay power.
    """
    res = irrigation_service.emergency_stop()
    return {"status": "SUCCESS", "emergency_stop": res}

@router.post("/actuators/reset-emergency-stop")
def reset_emergency_stop():
    """
    Clears emergency stop override.
    """
    res = irrigation_service.reset_emergency_stop()
    return {"status": "SUCCESS", "emergency_stop": res}

@router.get("/actuators/status")
def get_actuator_status():
    """
    Returns relay state, cooldown status, and safety limits.
    """
    res = irrigation_service.get_status()
    return {"status": "SUCCESS", "actuator_status": res}

@router.post("/simulation/digital-twin/set-scenario")
def set_digital_twin_scenario(req: SetScenarioRequest):
    """
    Updates SIL Digital Twin field simulation scenario.
    """
    res = digital_twin_service.set_scenario(req.scenario_name)
    return {"status": "SUCCESS", "digital_twin": res}

@router.get("/simulation/digital-twin/telemetry")
def get_digital_twin_telemetry(node_id: str = "NODE-01"):
    """
    Gets real-time simulated field telemetry from active SIL Digital Twin state.
    """
    res = digital_twin_service.generate_simulated_telemetry(node_id)
    return {"status": "SUCCESS", "simulated_telemetry": res}
