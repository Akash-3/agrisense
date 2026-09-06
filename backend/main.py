import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="AgriSense IoT Backend API",
    description="API server for processing IoT sensor telemetry from Drone & Ground nodes.",
    version="1.0.0"
)

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Data Schemas ---

class SpectralData(BaseModel):
    ch415nm: int = Field(520, description="415nm Violet channel raw reading")
    ch445nm: int = Field(610, description="445nm Indigo channel raw reading")
    ch480nm: int = Field(640, description="480nm Blue channel raw reading")
    ch515nm: int = Field(720, description="515nm Cyan channel raw reading")
    ch555nm: int = Field(690, description="555nm Green channel raw reading")
    ch590nm: int = Field(560, description="590nm Yellow channel raw reading")
    ch630nm: int = Field(470, description="630nm Orange channel raw reading")
    ch680nm: int = Field(410, description="680nm Red channel raw reading")
    clear: int = Field(1000, description="Clear channel broadband light")
    nir: int = Field(885, description="Near Infrared channel light reading")

class TelemetryPayload(BaseModel):
    device_id: str = Field(..., example="drone01")
    device_type: str = Field(..., example="drone")  # "drone" or "ground"
    temperature: Optional[float] = Field(None, example=30.4)
    humidity: Optional[float] = Field(None, example=74.2)
    mq2_raw: Optional[int] = Field(None, example=165)
    soil_moisture: Optional[float] = Field(None, example=48.5)
    spectral: Optional[SpectralData] = None
    timestamp: Optional[str] = None

# In-memory storage for rapid development / demonstration
telemetry_db: List[Dict] = []
alert_logs: List[Dict] = []

# Pre-populate with realistic baseline data
initial_time = datetime.datetime.now(datetime.timezone.utc)
for i in range(10):
    t_offset = initial_time - datetime.timedelta(minutes=(10 - i) * 5)
    
    # Drone reading
    drone_reading = {
        "id": len(telemetry_db) + 1,
        "device_id": "drone01",
        "device_type": "drone",
        "temperature": round(28.5 + (i * 0.3), 1),
        "humidity": round(70.0 - (i * 0.4), 1),
        "mq2_raw": 150 + (i * 5),
        "soil_moisture": None,
        "spectral": {
            "ch415nm": 500 + i*10,
            "ch445nm": 580 + i*8,
            "ch480nm": 620 + i*5,
            "ch515nm": 700 + i*6,
            "ch555nm": 670 + i*4,
            "ch590nm": 540 + i*5,
            "ch630nm": 450 + i*6,
            "ch680nm": 400 + i*5,
            "clear": 980 + i*15,
            "nir": 860 + (i * 12) if i % 2 == 0 else 620
        },
        "crop_health_status": "Healthy" if (860 + (i * 12) if i % 2 == 0 else 620) >= 850 else "Moderate Stress",
        "timestamp": t_offset.isoformat()
    }
    telemetry_db.append(drone_reading)
    
    # Ground reading
    ground_reading = {
        "id": len(telemetry_db) + 1,
        "device_id": "ground01",
        "device_type": "ground",
        "temperature": round(27.8 + (i * 0.2), 1),
        "humidity": round(72.0 - (i * 0.3), 1),
        "mq2_raw": None,
        "soil_moisture": round(55.0 - (i * 1.2), 1),
        "spectral": None,
        "crop_health_status": None,
        "timestamp": t_offset.isoformat()
    }
    telemetry_db.append(ground_reading)


def calculate_chi(nir_val: int) -> Dict[str, str]:
    if nir_val >= 850:
        return {
            "status": "Healthy",
            "badge": "🟢 Optimal Vigor",
            "color": "#10B981",
            "recommendation": "Crop vigor is optimal. Maintain current irrigation and fertilizer schedules."
        }
    elif nir_val >= 600:
        return {
            "status": "Moderate Stress",
            "badge": "🟡 Caution",
            "color": "#F59E0B",
            "recommendation": "Mild vegetative stress detected. Check soil moisture and micro-nutrient levels."
        }
    else:
        return {
            "status": "Poor",
            "badge": "🔴 Severe Deficit",
            "color": "#EF4444",
            "recommendation": "Significant crop stress or foliage deficit. Immediate field inspection recommended."
        }


@app.get("/")
def read_root():
    return {
        "system": "AgriSense Backend API",
        "status": "Online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.post("/api/v1/sensors", status_code=201)
def receive_sensor_telemetry(payload: TelemetryPayload):
    current_time = payload.timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    chi_info = None
    if payload.spectral and payload.spectral.nir is not None:
        chi_info = calculate_chi(payload.spectral.nir)
        
    entry = {
        "id": len(telemetry_db) + 1,
        "device_id": payload.device_id,
        "device_type": payload.device_type,
        "temperature": payload.temperature,
        "humidity": payload.humidity,
        "mq2_raw": payload.mq2_raw,
        "soil_moisture": payload.soil_moisture,
        "spectral": payload.spectral.dict() if payload.spectral else None,
        "crop_health_status": chi_info["status"] if chi_info else None,
        "timestamp": current_time
    }
    
    telemetry_db.append(entry)
    
    # Check for Hazard Alerts
    if payload.mq2_raw and payload.mq2_raw > 400:
        alert = {
            "id": len(alert_logs) + 1,
            "type": "FIRE_SMOKE_HAZARD",
            "severity": "CRITICAL",
            "message": f"High gas/smoke reading detected on {payload.device_id}: {payload.mq2_raw} PPM",
            "timestamp": current_time
        }
        alert_logs.append(alert)
        
    if payload.soil_moisture and payload.soil_moisture < 30.0:
        alert = {
            "id": len(alert_logs) + 1,
            "type": "LOW_SOIL_MOISTURE",
            "severity": "WARNING",
            "message": f"Soil moisture critically low on {payload.device_id}: {payload.soil_moisture}%",
            "timestamp": current_time
        }
        alert_logs.append(alert)

    return {
        "status": "success",
        "message": "Telemetry received and logged",
        "recorded_id": entry["id"],
        "chi": chi_info
    }


@app.get("/api/v1/sensors/latest")
def get_latest_telemetry():
    latest_drone = next((x for x in reversed(telemetry_db) if x["device_type"] == "drone"), None)
    latest_ground = next((x for x in reversed(telemetry_db) if x["device_type"] == "ground"), None)
    
    drone_chi = None
    if latest_drone and latest_drone.get("spectral"):
        drone_chi = calculate_chi(latest_drone["spectral"]["nir"])
        
    return {
        "drone": latest_drone,
        "ground": latest_ground,
        "chi": drone_chi
    }


@app.get("/api/v1/sensors/history")
def get_telemetry_history(limit: int = Query(50, ge=1, le=200)):
    return telemetry_db[-limit:]


@app.get("/api/v1/crop-health")
def get_crop_health_summary():
    drone_readings = [x for x in telemetry_db if x["device_type"] == "drone" and x.get("spectral")]
    if not drone_readings:
        return {"status": "No spectral data available"}
        
    latest_nir = drone_readings[-1]["spectral"]["nir"]
    chi_info = calculate_chi(latest_nir)
    
    # Calculate average NIR over history
    avg_nir = sum(x["spectral"]["nir"] for x in drone_readings) / len(drone_readings)
    
    return {
        "latest_nir": latest_nir,
        "average_nir": round(avg_nir, 1),
        "health_index": chi_info,
        "spectral_channels": drone_readings[-1]["spectral"]
    }


@app.get("/api/v1/dashboard")
def get_dashboard_summary():
    latest_drone = next((x for x in reversed(telemetry_db) if x["device_type"] == "drone"), None)
    latest_ground = next((x for x in reversed(telemetry_db) if x["device_type"] == "ground"), None)
    
    drone_chi = calculate_chi(latest_drone["spectral"]["nir"]) if (latest_drone and latest_drone.get("spectral")) else None
    
    return {
        "summary": {
            "drone_status": "ONLINE" if latest_drone else "OFFLINE",
            "ground_status": "ONLINE" if latest_ground else "OFFLINE",
            "temperature": latest_drone["temperature"] if latest_drone else None,
            "humidity": latest_drone["humidity"] if latest_drone else None,
            "mq2_gas_ppm": latest_drone["mq2_raw"] if latest_drone else None,
            "soil_moisture_pct": latest_ground["soil_moisture"] if latest_ground else None,
            "crop_health": drone_chi
        },
        "alerts": alert_logs[-5:],
        "recent_history": telemetry_db[-20:]
    }


@app.post("/api/v1/simulate")
def trigger_simulated_reading():
    import random
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    sim_nir = random.randint(550, 920)
    sim_drone = TelemetryPayload(
        device_id="drone01",
        device_type="drone",
        temperature=round(27.0 + random.uniform(0, 6.0), 1),
        humidity=round(60.0 + random.uniform(0, 20.0), 1),
        mq2_raw=random.randint(140, 220),
        spectral=SpectralData(
            ch415nm=random.randint(480, 560),
            ch445nm=random.randint(550, 630),
            ch480nm=random.randint(600, 680),
            ch515nm=random.randint(680, 760),
            ch555nm=random.randint(640, 720),
            ch590nm=random.randint(500, 600),
            ch630nm=random.randint(420, 500),
            ch680nm=random.randint(380, 450),
            clear=random.randint(900, 1100),
            nir=sim_nir
        ),
        timestamp=now_str
    )
    
    sim_ground = TelemetryPayload(
        device_id="ground01",
        device_type="ground",
        soil_moisture=round(35.0 + random.uniform(0, 30.0), 1),
        temperature=round(26.0 + random.uniform(0, 5.0), 1),
        humidity=round(62.0 + random.uniform(0, 15.0), 1),
        timestamp=now_str
    )
    
    r1 = receive_sensor_telemetry(sim_drone)
    r2 = receive_sensor_telemetry(sim_ground)
    
    return {
        "simulated": True,
        "drone_result": r1,
        "ground_result": r2
    }
