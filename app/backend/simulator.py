import asyncio
import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class TelemetryPayload(BaseModel):
    device_id: str = Field(..., example="ESP32_SOIL_NODE_01")
    node_type: str = Field(default="ground_soil")
    timestamp: float = Field(default_factory=time.time)
    is_real_hardware: bool = Field(default=False)
    
    # 10-Channel AS7341 Multi-Spectral Sensor Optical Counts (Counts / Raw)
    f1_415nm: int = Field(default=450, ge=0)
    f2_445nm: int = Field(default=680, ge=0)
    f3_480nm: int = Field(default=920, ge=0)
    f4_515nm: int = Field(default=1450, ge=0)
    f5_555nm: int = Field(default=2800, ge=0)
    f6_590nm: int = Field(default=1600, ge=0)
    f7_630nm: int = Field(default=980, ge=0)
    f8_680nm: int = Field(default=480, ge=0)
    clear_channel: int = Field(default=12400, ge=0)
    nir_885nm: int = Field(default=6800, ge=0)
    
    # Environmental & Soil Telemetry
    soil_moisture_vwc: Optional[float] = Field(default=42.5)
    temperature_c: Optional[float] = Field(default=26.1)
    humidity_pct: Optional[float] = Field(default=68.4)
    smoke_ppm: Optional[float] = Field(default=80.0)
    soil_status: Optional[str] = Field(default="SENSOR_DISCONNECTED")
    dht_status: Optional[str] = Field(default="SENSOR_DISCONNECTED")
    mq135_status: Optional[str] = Field(default="SENSOR_DISCONNECTED")

class AIDiagnosticResult(BaseModel):
    status: str
    pathogen_risk_pct: float
    crop_health_index: float
    pre_symptomatic_lead_days: float
    recommended_action: str
    hazard_alert: Optional[str] = None
    sensor_fault_alert: Optional[str] = None

class SimulationEngine:
    """
    Executes deterministic MM-SSNet dual-stream AI diagnostic inference for hardware telemetry data.
    """
    def __init__(self):
        self.preset_state = "HEALTHY"
        self.last_hardware_packet_at = 0.0

    def compute_mm_ssnet_inference(self, payload: TelemetryPayload) -> AIDiagnosticResult:
        red = max(1, payload.f8_680nm)
        nir = payload.nir_885nm
        green = max(1, payload.f5_555nm)
        
        r_cri = (nir - red) / (nir + red) if (nir + red) > 0 else 0.0
        s_nir = nir / green if green > 0 else 1.0
        
        chi = round((r_cri * 70.0) + (s_nir * 10.0), 2)
        
        hazard_alert = None
        sensor_faults = []
        if payload.soil_status == "SENSOR_DISCONNECTED" or payload.soil_moisture_vwc is None:
            sensor_faults.append("Soil Moisture Sensor DOWN")
        if payload.dht_status == "SENSOR_DISCONNECTED" or payload.temperature_c is None:
            sensor_faults.append("DHT22 Temp/Humidity Sensor DOWN")
        if payload.mq135_status == "SENSOR_DISCONNECTED" or payload.smoke_ppm is None:
            sensor_faults.append("MQ-135 Air Quality Sensor DOWN")

        sensor_fault_alert = f"⚠️ HARDWARE WARNING: {', '.join(sensor_faults)}" if sensor_faults else None

        if payload.smoke_ppm is not None and payload.smoke_ppm > 400.0:
            status = "SMOKE_HAZARD"
            risk = 92.5
            lead_days = 0.0
            rec = "🔥 CRITICAL: Stubble Fire / Smoke Hazard detected! Trigger emergency agricultural field alarm."
            hazard_alert = f"STUBBLE FIRE HAZARD: Smoke level {payload.smoke_ppm:.1f} PPM exceeds safe 400 PPM threshold!"
        elif payload.soil_moisture_vwc is not None and payload.soil_moisture_vwc < 30.0:
            status = "SEVERE_DROUGHT"
            risk = 88.0
            lead_days = 0.0
            rec = "💧 CRITICAL: Soil hydration deficit! Activate drip irrigation system immediately to prevent root death."
            hazard_alert = f"SOIL DROUGHT ALERT: Volumetric Soil Water Content ({payload.soil_moisture_vwc:.1f}%) is below 30%!"
        elif r_cri < 0.55 or s_nir < 1.8:
            status = "PRE_SYMPTOMATIC_STRESS"
            risk = 48.2
            lead_days = 5.4
            rec = "⚡ PRE-SYMPTOMATIC ALERT: Internal mesophyll NIR breakdown detected! Apply bio-fungicide within 48 hours."
        else:
            status = "HEALTHY"
            risk = 9.9
            lead_days = 0.0
            rec = "✅ Optimal Crop Health: Leaf canopy NIR scattering & soil hydration levels are within ideal ranges."

        return AIDiagnosticResult(
            status=status,
            pathogen_risk_pct=risk,
            crop_health_index=chi,
            pre_symptomatic_lead_days=lead_days,
            recommended_action=rec,
            hazard_alert=hazard_alert,
            sensor_fault_alert=sensor_fault_alert
        )

    def generate_telemetry(self, preset: Optional[str] = None) -> TelemetryPayload:
        if preset:
            self.preset_state = preset

        p = TelemetryPayload(
            device_id="ESP32_SOIL_NODE_01",
            node_type="ground_soil",
            timestamp=time.time(),
            is_real_hardware=False
        )

        if self.preset_state == "HEALTHY":
            p.f1_415nm = 450
            p.f2_445nm = 680
            p.f3_480nm = 920
            p.f4_515nm = 1450
            p.f5_555nm = 2800
            p.f6_590nm = 1600
            p.f7_630nm = 980
            p.f8_680nm = 480
            p.nir_885nm = 6800
            p.soil_moisture_vwc = 42.5
            p.temperature_c = 26.1
            p.humidity_pct = 68.4
            p.smoke_ppm = 80.0

        elif self.preset_state == "PRE_SYMPTOMATIC_STRESS":
            p.f1_415nm = 460
            p.f2_445nm = 700
            p.f3_480nm = 950
            p.f4_515nm = 1480
            p.f5_555nm = 2650
            p.f6_590nm = 1820
            p.f7_630nm = 1150
            p.f8_680nm = 920
            p.nir_885nm = 3100
            p.soil_moisture_vwc = 38.0
            p.temperature_c = 28.4
            p.humidity_pct = 58.0
            p.smoke_ppm = 95.0

        elif self.preset_state == "SEVERE_DROUGHT":
            p.f1_415nm = 480
            p.f2_445nm = 720
            p.f3_480nm = 980
            p.f4_515nm = 1520
            p.f5_555nm = 2100
            p.f6_590nm = 2100
            p.f7_630nm = 1450
            p.f8_680nm = 1200
            p.nir_885nm = 2800
            p.soil_moisture_vwc = 14.2
            p.temperature_c = 36.5
            p.humidity_pct = 28.0
            p.smoke_ppm = 110.0

        elif self.preset_state == "SMOKE_HAZARD":
            p.f1_415nm = 520
            p.f2_445nm = 780
            p.f3_480nm = 1050
            p.f4_515nm = 1600
            p.f5_555nm = 2400
            p.f6_590nm = 2300
            p.f7_630nm = 1600
            p.f8_680nm = 1100
            p.nir_885nm = 4100
            p.soil_moisture_vwc = 22.0
            p.temperature_c = 38.2
            p.humidity_pct = 35.0
            p.smoke_ppm = 485.0

        p.clear_channel = sum([p.f1_415nm, p.f2_445nm, p.f3_480nm, p.f4_515nm, p.f5_555nm, p.f6_590nm, p.f7_630nm, p.f8_680nm])
        return p

simulator = SimulationEngine()
