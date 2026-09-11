import numpy as np
import time

class DigitalTwinService:
    """
    Software-In-The-Loop (SIL) Digital Twin Field Simulator.
    Simulates physical field environments, crop canopy response, sensor drift, and extreme weather events.
    """

    def __init__(self):
        self.active_scenario = "HEALTHY_FIELD"
        self.simulation_time_step = 0

    def set_scenario(self, scenario_name):
        valid_scenarios = [
            "REAL_HARDWARE",
            "HEALTHY_FIELD",
            "WATER_STRESS_EPISODE",
            "FUNGAL_DISEASE_OUTBREAK",
            "SENSOR_DEGRADATION",
            "GPS_LOSS"
        ]
        if scenario_name not in valid_scenarios:
            scenario_name = "HEALTHY_FIELD"
        
        self.active_scenario = scenario_name
        return {
            "active_scenario": self.active_scenario,
            "message": f"SIL Digital Twin scenario updated to {self.active_scenario}"
        }

    def generate_simulated_telemetry(self, node_id="NODE-01"):
        """
        Generates simulated telemetry matching current SIL Digital Twin scenario.
        """
        self.simulation_time_step += 1
        t = self.simulation_time_step

        if self.active_scenario == "HEALTHY_FIELD":
            temp = round(23.5 + 2.0 * np.sin(t * 0.1), 1)
            hum = round(65.0 + 5.0 * np.cos(t * 0.1), 1)
            soil = round(52.0 - 0.5 * (t % 10), 1)
            smoke = round(75.0 + np.random.normal(0, 5), 1)
            # AS7341 healthy spectral signature
            spectral = [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]

        elif self.active_scenario == "WATER_STRESS_EPISODE":
            temp = round(34.0 + 3.0 * np.sin(t * 0.1), 1)
            hum = round(30.0 - 2.0 * (t % 5), 1)
            soil = round(18.0 - 1.2 * (t % 10), 1) # Depleting moisture
            smoke = round(88.0 + np.random.normal(0, 5), 1)
            # Water stress spectral signature (NIR drop)
            spectral = [0.18, 0.22, 0.25, 0.30, 0.45, 0.55, 0.50, 0.45, 0.48, 0.52]

        elif self.active_scenario == "FUNGAL_DISEASE_OUTBREAK":
            temp = round(26.0 + np.random.normal(0, 1), 1)
            hum = round(88.0 + 3.0 * np.sin(t * 0.2), 1) # High humidity
            soil = round(45.0, 1)
            smoke = round(120.0 + np.random.normal(0, 10), 1)
            # Fungal disease spectral signature (green reflectance drop, red elevation)
            spectral = [0.22, 0.25, 0.28, 0.28, 0.38, 0.50, 0.58, 0.52, 0.42, 0.45]

        elif self.active_scenario == "SENSOR_DEGRADATION":
            temp = -999.0 # Faulty reading
            hum = round(12.0, 1)
            soil = 100.0
            smoke = 999.9 # Faulty sensor voltage
            spectral = [0.0] * 10

        elif self.active_scenario == "GPS_LOSS":
            temp = 25.0
            hum = 60.0
            soil = 50.0
            smoke = 80.0
            spectral = [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]

        else: # Default
            temp = 24.0
            hum = 60.0
            soil = 50.0
            smoke = 80.0
            spectral = [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]

        return {
            "node_id": node_id,
            "scenario": self.active_scenario,
            "temperature": temp,
            "humidity": hum,
            "soil_moisture": soil,
            "smoke_ppm": smoke,
            "spectral": spectral,
            "simulated_time_step": t,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

digital_twin_service = DigitalTwinService()
