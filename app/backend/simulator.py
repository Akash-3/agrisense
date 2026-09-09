import asyncio
import random
import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class TelemetryPayload(BaseModel):
    device_id: str = Field(..., example="AGRI-DRONE-PAYLOAD-01")
    node_type: str = Field(..., example="aerial_drone") # 'aerial_drone' or 'ground_soil'
    timestamp: float = Field(default_factory=time.time)
    
    # 10-Channel AS7341 Multi-Spectral Sensor Optical Counts (Counts / Raw)
    f1_415nm: int = Field(default=450, ge=0) # Violet
    f2_445nm: int = Field(default=680, ge=0) # Indigo
    f3_480nm: int = Field(default=920, ge=0) # Blue
    f4_515nm: int = Field(default=1450, ge=0) # Cyan
    f5_555nm: int = Field(default=2800, ge=0) # Green (Peak Healthy Chlorophyll)
    f6_590nm: int = Field(default=1600, ge=0) # Yellow
    f7_630nm: int = Field(default=980, ge=0) # Orange
    f8_680nm: int = Field(default=520, ge=0) # Red (Chlorophyll Absorption Dip)
    clear_channel: int = Field(default=12400, ge=0) # Broadband Visible
    nir_885nm: int = Field(default=6400, ge=0) # Near-Infrared Scattering (Cellular Health)
    
    # Environmental & Soil Telemetry
    soil_moisture_vwc: Optional[float] = Field(default=65.4) # Soil VWC%
    temperature_c: Optional[float] = Field(default=26.5) # Microclimate Temp °C
    humidity_pct: Optional[float] = Field(default=62.0) # Relative Humidity %
    smoke_ppm: Optional[float] = Field(default=85.0) # MQ-2 Gas/Smoke Level
    soil_status: Optional[str] = Field(default="ONLINE")
    dht_status: Optional[str] = Field(default="ONLINE")
    mq135_status: Optional[str] = Field(default="ONLINE")

class AIDiagnosticResult(BaseModel):
    status: str # 'HEALTHY', 'PRE_SYMPTOMATIC_STRESS', 'SEVERE_DROUGHT', 'SMOKE_HAZARD', 'SENSOR_FAULT'
    pathogen_risk_pct: float
    crop_health_index: float # R_CRI & S_NIR combined index
    pre_symptomatic_lead_days: float
    recommended_action: str
    hazard_alert: Optional[str] = None
    sensor_fault_alert: Optional[str] = None

class SimulationEngine:
    """
    Generates realistic, physically valid telemetry streams and executes
    MM-SSNet dual-stream AI inference for live demo and testing.
    """
    def __init__(self):
        self.preset_state = "HEALTHY"
        self.auto_stream = True

    def compute_mm_ssnet_inference(self, payload: TelemetryPayload) -> AIDiagnosticResult:
        # Calculate Crop Health Index (CHI) from 10-channel optics
        # Healthy plants absorb red (680nm) and heavily scatter NIR (885nm)
        red = max(1, payload.f8_680nm)
        nir = payload.nir_885nm
        green = payload.f5_555nm
        
        # NDVI-equivalent Crop Reflectance Index (R_CRI)
        r_cri = (nir - red) / (nir + red) if (nir + red) > 0 else 0.0
        s_nir = nir / green if green > 0 else 1.0
        
        chi = round((r_cri * 70.0) + (s_nir * 10.0), 2)
        
        # Determine Pathogen & Hazard State
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
            risk = round(random.uniform(74.0, 91.0), 1)
            lead_days = 5.4
            rec = "⚡ PRE-SYMPTOMATIC ALERT: Internal mesophyll NIR breakdown detected! Apply bio-fungicide within 48 hours."
        else:
            status = "HEALTHY"
            risk = round(random.uniform(3.0, 12.0), 1)
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
            device_id="AGRI-DRONE-PAYLOAD-01",
            node_type="aerial_drone",
            timestamp=time.time()
        )

        if self.preset_state == "HEALTHY":
            p.f1_415nm = int(random.gauss(450, 20))
            p.f2_445nm = int(random.gauss(680, 25))
            p.f3_480nm = int(random.gauss(920, 30))
            p.f4_515nm = int(random.gauss(1450, 40))
            p.f5_555nm = int(random.gauss(2800, 60)) # Peak Green
            p.f6_590nm = int(random.gauss(1600, 40))
            p.f7_630nm = int(random.gauss(980, 30))
            p.f8_680nm = int(random.gauss(480, 20))  # Low Red (Absorption)
            p.nir_885nm = int(random.gauss(6800, 100)) # High NIR (Scattering)
            p.soil_moisture_vwc = round(random.gauss(68.5, 1.5), 1)
            p.temperature_c = round(random.gauss(26.2, 0.5), 1)
            p.humidity_pct = round(random.gauss(62.0, 1.0), 1)
            p.smoke_ppm = round(random.gauss(78.0, 5.0), 1)

        elif self.preset_state == "PRE_SYMPTOMATIC_STRESS":
            # Asymptomatic Fungal Rust / Stress: NIR drops before visible leaf yellowing
            p.f1_415nm = int(random.gauss(460, 20))
            p.f2_445nm = int(random.gauss(700, 25))
            p.f3_480nm = int(random.gauss(950, 30))
            p.f4_515nm = int(random.gauss(1480, 40))
            p.f5_555nm = int(random.gauss(2650, 60)) # Green slightly down
            p.f6_590nm = int(random.gauss(1820, 40)) # Yellow slightly up
            p.f7_630nm = int(random.gauss(1150, 30))
            p.f8_680nm = int(random.gauss(920, 30))  # Red absorption weakening
            p.nir_885nm = int(random.gauss(3100, 80)) # NIR scattering Breakdown! (Key Indicator)
            p.soil_moisture_vwc = round(random.gauss(61.0, 1.5), 1)
            p.temperature_c = round(random.gauss(27.8, 0.5), 1)
            p.humidity_pct = round(random.gauss(58.0, 1.0), 1)
            p.smoke_ppm = round(random.gauss(85.0, 5.0), 1)

        elif self.preset_state == "SEVERE_DROUGHT":
            # Low Soil VWC < 30%
            p.f1_415nm = int(random.gauss(480, 20))
            p.f2_445nm = int(random.gauss(720, 25))
            p.f3_480nm = int(random.gauss(980, 30))
            p.f4_515nm = int(random.gauss(1520, 40))
            p.f5_555nm = int(random.gauss(2100, 60))
            p.f6_590nm = int(random.gauss(2100, 40))
            p.f7_630nm = int(random.gauss(1450, 30))
            p.f8_680nm = int(random.gauss(1200, 30))
            p.nir_885nm = int(random.gauss(2800, 80))
            p.soil_moisture_vwc = round(random.gauss(21.4, 1.0), 1) # Low VWC% < 30%
            p.temperature_c = round(random.gauss(34.5, 0.8), 1) # High Temp
            p.humidity_pct = round(random.gauss(28.0, 1.5), 1)  # Low Humidity
            p.smoke_ppm = round(random.gauss(110.0, 8.0), 1)

        elif self.preset_state == "SMOKE_HAZARD":
            # Stubble Fire Smoke > 400 PPM
            p.f1_415nm = int(random.gauss(520, 20))
            p.f2_445nm = int(random.gauss(780, 25))
            p.f3_480nm = int(random.gauss(1050, 30))
            p.f4_515nm = int(random.gauss(1600, 40))
            p.f5_555nm = int(random.gauss(2400, 60))
            p.f6_590nm = int(random.gauss(2300, 40))
            p.f7_630nm = int(random.gauss(1600, 30))
            p.f8_680nm = int(random.gauss(1100, 30))
            p.nir_885nm = int(random.gauss(4100, 90))
            p.soil_moisture_vwc = round(random.gauss(42.0, 2.0), 1)
            p.temperature_c = round(random.gauss(38.2, 1.0), 1)
            p.humidity_pct = round(random.gauss(35.0, 2.0), 1)
            p.smoke_ppm = round(random.gauss(585.0, 25.0), 1) # High Smoke > 400 PPM

        p.clear_channel = sum([p.f1_415nm, p.f2_445nm, p.f3_480nm, p.f4_515nm, p.f5_555nm, p.f6_590nm, p.f7_630nm, p.f8_680nm])
        return p

simulator = SimulationEngine()
