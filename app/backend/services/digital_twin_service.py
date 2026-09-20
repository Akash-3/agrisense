import numpy as np
import time

class DigitalTwinService:
    """
    Software-In-The-Loop (SIL) Digital Twin Field Simulator.
    Simulates physical field environments, crop canopy response, sensor drift, and extreme weather events.

    Phase 11: Scenario state is scoped per authenticated user (user_id) to prevent
    cross-tenant contamination.  User A changing a scenario does NOT affect User B.
    """

    def __init__(self):
        # Per-user scenario state: {user_id: scenario_name}
        self._user_scenarios: dict = {}
        # Per-user simulation time step: {user_id: int}
        self._user_time_steps: dict = {}
        # Legacy global default (only used before first user sets a scenario)
        self._default_scenario = "HEALTHY_FIELD"

    def _get_scenario(self, user_id=None):
        if user_id is not None:
            return self._user_scenarios.get(user_id, self._default_scenario)
        return self._default_scenario

    def _next_time_step(self, user_id=None):
        if user_id is not None:
            self._user_time_steps[user_id] = self._user_time_steps.get(user_id, 0) + 1
            return self._user_time_steps[user_id]
        return 1

    def set_scenario(self, scenario_name, user_id=None):
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

        if user_id is not None:
            self._user_scenarios[user_id] = scenario_name
        else:
            self._default_scenario = scenario_name

        return {
            "active_scenario": scenario_name,
            "message": f"SIL Digital Twin scenario updated to {scenario_name}"
        }

    def generate_simulated_telemetry(self, node_id="NODE-01", user_id=None):
        """
        Generates simulated telemetry matching the current SIL Digital Twin scenario
        for the given user tenant.
        """
        t = self._next_time_step(user_id)
        scenario = self._get_scenario(user_id)

        if scenario == "HEALTHY_FIELD":
            temp = round(23.5 + 2.0 * np.sin(t * 0.1), 1)
            hum = round(65.0 + 5.0 * np.cos(t * 0.1), 1)
            soil = round(52.0 - 0.5 * (t % 10), 1)
            smoke = round(75.0 + np.random.normal(0, 5), 1)
            # AS7341 healthy spectral signature
            spectral = [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]

        elif scenario == "WATER_STRESS_EPISODE":
            temp = round(34.0 + 3.0 * np.sin(t * 0.1), 1)
            hum = round(30.0 - 2.0 * (t % 5), 1)
            soil = round(18.0 - 1.2 * (t % 10), 1) # Depleting moisture
            smoke = round(88.0 + np.random.normal(0, 5), 1)
            # Water stress spectral signature (NIR drop)
            spectral = [0.18, 0.22, 0.25, 0.30, 0.45, 0.55, 0.50, 0.45, 0.48, 0.52]

        elif scenario == "FUNGAL_DISEASE_OUTBREAK":
            temp = round(26.0 + np.random.normal(0, 1), 1)
            hum = round(88.0 + 3.0 * np.sin(t * 0.2), 1) # High humidity
            soil = round(45.0, 1)
            smoke = round(120.0 + np.random.normal(0, 10), 1)
            # Fungal disease spectral signature (green reflectance drop, red elevation)
            spectral = [0.22, 0.25, 0.28, 0.28, 0.38, 0.50, 0.58, 0.52, 0.42, 0.45]

        elif scenario == "SENSOR_DEGRADATION":
            temp = -999.0 # Faulty reading
            hum = round(12.0, 1)
            soil = 100.0
            smoke = 999.9 # Faulty sensor voltage
            spectral = [0.0] * 10

        elif scenario == "GPS_LOSS":
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
            "scenario": scenario,
            "temperature": temp,
            "humidity": hum,
            "soil_moisture": soil,
            "smoke_ppm": smoke,
            "spectral": spectral,
            "simulated_time_step": t,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

digital_twin_service = DigitalTwinService()
