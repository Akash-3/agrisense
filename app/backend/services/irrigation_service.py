import time
import requests

class RelayAdapter:
    """
    Abstract Hardware Relay Adapter Interface.
    """
    def send_relay_command(self, zone_id, state, duration_sec=0):
        raise NotImplementedError

class SimulationRelayAdapter(RelayAdapter):
    """
    Software simulation relay adapter for testing and SIL Digital Twin mode.
    """
    MODE = "SIMULATED_RELAY"

    def send_relay_command(self, zone_id, state, duration_sec=0):
        print(f"[SimulationRelayAdapter] Software relay state set to {state} for Zone '{zone_id}' ({duration_sec}s)")
        return {"success": True, "relay_mode": self.MODE, "hardware_dispatched": False}

class ESP32RelayAdapter(RelayAdapter):
    """
    Real ESP32 Hardware Relay Adapter sending REST/HTTP actuation commands over local IP.
    """
    MODE = "REAL_RELAY"

    def __init__(self, esp32_ip="http://192.168.1.100"):
        self.esp32_ip = esp32_ip

    def send_relay_command(self, zone_id, state, duration_sec=0):
        url = f"{self.esp32_ip}/api/actuator/relay"
        try:
            res = requests.post(url, json={"zone_id": zone_id, "state": state, "duration_sec": duration_sec}, timeout=3.0)
            if res.status_code == 200:
                return {"success": True, "relay_mode": self.MODE, "hardware_dispatched": True}
        except Exception as e:
            print(f"[ESP32RelayAdapter] Hardware REST dispatch error to {url}: {e}")
        return {"success": False, "relay_mode": self.MODE, "hardware_dispatched": False, "error": "ESP32 hardware unreachable"}


class IrrigationService:
    """
    Closed-Loop Irrigation Engine with Hardware Safety Limits & Pluggable Relay Adapters.
    """
    def __init__(self, adapter=None):
        self.adapter = adapter or SimulationRelayAdapter()
        self.last_actuation_time = 0.0
        self.cooldown_period_sec = 900.0 # 15 minutes
        self.max_duration_sec = 300.0   # 5 minutes max
        self.emergency_stop_active = False
        self.software_relay_state = "OFF"
        self.actuation_history = []

    def set_adapter(self, adapter):
        self.adapter = adapter

    def trigger_actuator(self, zone_id, duration_sec=60, trigger_source="AI_CLOSED_LOOP"):
        current_time = time.time()

        if duration_sec <= 0:
            return {
            "success": False,
            "status": "INVALID_DURATION",
            "message": "Actuation duration must be greater than 0 seconds.",
            "relay_state": "OFF",
            "relay_mode": self.adapter.MODE
            }

        if self.emergency_stop_active:
            return {
                "success": False,
                "status": "BLOCKED_EMERGENCY_STOP",
                "message": "Actuation rejected: Emergency Stop is ACTIVE.",
                "relay_state": "OFF",
                "relay_mode": self.adapter.MODE
            }

        if duration_sec > self.max_duration_sec:
            duration_sec = self.max_duration_sec

        time_since_last = current_time - self.last_actuation_time
        if self.last_actuation_time > 0 and time_since_last < self.cooldown_period_sec:
            remaining_cooldown = round(self.cooldown_period_sec - time_since_last, 1)
            return {
                "success": False,
                "status": "BLOCKED_COOLDOWN_ACTIVE",
                "message": f"Actuation rejected: Safety cooldown active ({remaining_cooldown}s remaining).",
                "cooldown_remaining_sec": remaining_cooldown,
                "relay_state": "OFF",
                "relay_mode": self.adapter.MODE
            }

        # Dispatch through hardware adapter
        dispatch_res = self.adapter.send_relay_command(
            zone_id, "ON", duration_sec
        )
        
        if not dispatch_res.get("success", False):
            return {
                "success": False,
                "status": "ACTUATION_FAILED",
                "message": "Relay actuation failed: hardware adapter did not confirm dispatch.",
                "duration_sec": duration_sec,
                "zone_id": zone_id,
                "relay_state": "OFF",
                "relay_mode": self.adapter.MODE,
                "hardware_dispatched": False,
                "error": dispatch_res.get("error", "Unknown relay adapter error")
            }
        self.software_relay_state = "ON"
        self.last_actuation_time = current_time

        record = {
            "actuation_id": f"ACT-{int(current_time)}",
            "zone_id": zone_id,
            "duration_sec": duration_sec,
            "trigger_source": trigger_source,
            "relay_mode": self.adapter.MODE,
            "hardware_dispatched": True,
            "status": "DISPATCHED",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))
        }
        self.actuation_history.append(record)

        return {
            "success": True,
            "status": "ACTUATION_EXECUTED",
            "message": f"Relay actuation command ({self.adapter.MODE}) sent for Zone {zone_id} ({duration_sec}s).",
            "duration_sec": duration_sec,
            "zone_id": zone_id,
            "relay_state": "ON",
            "relay_mode": self.adapter.MODE,
            "hardware_dispatched": dispatch_res.get("hardware_dispatched", False)
        }

    def emergency_stop(self):
        dispatch_res = self.adapter.send_relay_command(
            "ALL_ZONES", "OFF", 0
        )

        self.emergency_stop_active = True
        self.software_relay_state = "OFF"

        return {
            "emergency_stop": True,
            "relay_state": "OFF",
            "relay_mode": self.adapter.MODE,
            "hardware_dispatched": dispatch_res.get(
                "hardware_dispatched",
                False
            ),
            "hardware_command_success": dispatch_res.get(
                "success",
                False
            ),
            "message": "EMERGENCY STOP ACTIVATED. All relays commanded OFF."
        }

    def reset_emergency_stop(self):
        self.emergency_stop_active = False
        return {
            "emergency_stop": False,
            "relay_mode": self.adapter.MODE,
            "message": "Emergency stop cleared. Relays returned to normal operation."
        }

    def get_status(self):
        time_since_last = time.time() - self.last_actuation_time
        in_cooldown = (self.last_actuation_time > 0) and (time_since_last < self.cooldown_period_sec)
        cooldown_rem = max(0.0, self.cooldown_period_sec - time_since_last) if in_cooldown else 0.0

        return {
            "relay_state": self.software_relay_state,
            "relay_mode": self.adapter.MODE,
            "emergency_stop_active": self.emergency_stop_active,
            "in_cooldown": in_cooldown,
            "cooldown_remaining_sec": round(cooldown_rem, 1),
            "actuation_count": len(self.actuation_history)
        }

irrigation_service = IrrigationService()
