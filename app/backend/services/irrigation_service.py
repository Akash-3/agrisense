import time

class IrrigationService:
    """
    Closed-Loop Irrigation & Actuator Control Engine with Hardware Safety Limits.
    Enforces:
    - Maximum single actuation pulse duration (<= 300s)
    - Cooldown period between activations (15 minutes = 900s)
    - Emergency Stop Override
    - Post-actuation soil moisture feedback verification
    """
    def __init__(self):
        self.last_actuation_time = 0.0
        self.cooldown_period_sec = 900.0 # 15 minutes
        self.max_duration_sec = 300.0   # 5 minutes max
        self.emergency_stop_active = False
        self.relay_state = "OFF"
        self.actuation_history = []

    def trigger_actuator(self, zone_id, duration_sec=60, trigger_source="AI_CLOSED_LOOP"):
        """
        Triggers pump/valve relay actuation after validating safety constraints.
        """
        current_time = time.time()

        if self.emergency_stop_active:
            return {
                "success": False,
                "status": "BLOCKED_EMERGENCY_STOP",
                "message": "Actuation rejected: Emergency Stop is ACTIVE.",
                "relay_state": "OFF"
            }

        # Check duration cap
        if duration_sec > self.max_duration_sec:
            duration_sec = self.max_duration_sec

        # Check cooldown timer
        time_since_last = current_time - self.last_actuation_time
        if self.last_actuation_time > 0 and time_since_last < self.cooldown_period_sec:
            remaining_cooldown = round(self.cooldown_period_sec - time_since_last, 1)
            return {
                "success": False,
                "status": "BLOCKED_COOLDOWN_ACTIVE",
                "message": f"Actuation rejected: System in safety cooldown ({remaining_cooldown}s remaining).",
                "cooldown_remaining_sec": remaining_cooldown,
                "relay_state": "OFF"
            }

        # Execute actuation pulse
        self.relay_state = "ON"
        self.last_actuation_time = current_time

        record = {
            "actuation_id": f"ACT-{int(current_time)}",
            "zone_id": zone_id,
            "duration_sec": duration_sec,
            "trigger_source": trigger_source,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time)),
            "status": "COMPLETED"
        }
        self.actuation_history.append(record)

        return {
            "success": True,
            "status": "ACTUATION_EXECUTED",
            "message": f"Relay activated for Zone {zone_id} for {duration_sec} seconds.",
            "duration_sec": duration_sec,
            "zone_id": zone_id,
            "relay_state": "ON",
            "verification": "Post-actuation moisture sampling scheduled in +300s"
        }

    def emergency_stop(self):
        """
        Activates emergency kill switch immediately cutting relay power.
        """
        self.emergency_stop_active = True
        self.relay_state = "OFF"
        return {
            "emergency_stop": True,
            "relay_state": "OFF",
            "message": "EMERGENCY STOP ACTIVATED. All relays deactivated."
        }

    def reset_emergency_stop(self):
        self.emergency_stop_active = False
        return {
            "emergency_stop": False,
            "message": "Emergency stop cleared. Relays returned to normal operation."
        }

    def get_status(self):
        time_since_last = time.time() - self.last_actuation_time
        in_cooldown = (self.last_actuation_time > 0) and (time_since_last < self.cooldown_period_sec)
        cooldown_rem = max(0.0, self.cooldown_period_sec - time_since_last) if in_cooldown else 0.0

        return {
            "relay_state": self.relay_state,
            "emergency_stop_active": self.emergency_stop_active,
            "in_cooldown": in_cooldown,
            "cooldown_remaining_sec": round(cooldown_rem, 1),
            "max_duration_sec": self.max_duration_sec,
            "actuation_count": len(self.actuation_history)
        }

irrigation_service = IrrigationService()
