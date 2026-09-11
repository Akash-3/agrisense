import unittest
import time
from app.backend.services.irrigation_service import IrrigationService

class TestClosedLoopActuators(unittest.TestCase):
    def setUp(self):
        self.service = IrrigationService()

    def test_actuation_and_cooldown(self):
        # 1. Trigger actuation
        res1 = self.service.trigger_actuator("ZONE-A", duration_sec=30)
        self.assertTrue(res1["success"])
        self.assertEqual(res1["relay_state"], "ON")

        # 2. Immediate second trigger should be blocked by cooldown
        res2 = self.service.trigger_actuator("ZONE-A", duration_sec=30)
        self.assertFalse(res2["success"])
        self.assertEqual(res2["status"], "BLOCKED_COOLDOWN_ACTIVE")

    def test_emergency_stop(self):
        self.service.emergency_stop()
        res = self.service.trigger_actuator("ZONE-A", duration_sec=30)
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "BLOCKED_EMERGENCY_STOP")

if __name__ == "__main__":
    unittest.main()
