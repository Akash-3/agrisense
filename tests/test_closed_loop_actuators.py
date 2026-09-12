import unittest
from app.backend.services.irrigation_service import IrrigationService


class MockRelayAdapter:
    """
    Test-only relay adapter.

    Records every relay command so the irrigation service can be
    tested without requiring a real ESP32.
    """
    MODE = "TEST_RELAY"

    def __init__(self, success=True):
        self.success = success
        self.commands = []

    def send_relay_command(self, zone_id, state, duration_sec=0):
        self.commands.append({
            "zone_id": zone_id,
            "state": state,
            "duration_sec": duration_sec
        })

        return {
            "success": self.success,
            "relay_mode": self.MODE,
            "hardware_dispatched": self.success
        }


class TestClosedLoopActuators(unittest.TestCase):

    def setUp(self):
        self.adapter = MockRelayAdapter()
        self.service = IrrigationService(adapter=self.adapter)

    def test_actuation_and_cooldown(self):
        # 1. Trigger actuation
        res1 = self.service.trigger_actuator(
            "ZONE-A",
            duration_sec=30
        )

        self.assertTrue(res1["success"])
        self.assertEqual(res1["relay_state"], "ON")

        # 2. Immediate second trigger should be blocked by cooldown
        res2 = self.service.trigger_actuator(
            "ZONE-A",
            duration_sec=30
        )

        self.assertFalse(res2["success"])
        self.assertEqual(
            res2["status"],
            "BLOCKED_COOLDOWN_ACTIVE"
        )

    def test_emergency_stop(self):
        self.service.emergency_stop()

        res = self.service.trigger_actuator(
            "ZONE-A",
            duration_sec=30
        )

        self.assertFalse(res["success"])
        self.assertEqual(
            res["status"],
            "BLOCKED_EMERGENCY_STOP"
        )

    def test_max_duration_enforced(self):
        # Request more than the 300-second safety limit.
        res = self.service.trigger_actuator(
            "ZONE-A",
            duration_sec=600
        )

        self.assertTrue(res["success"])

        # Service must clamp the duration to 300 seconds.
        self.assertEqual(
            res["duration_sec"],
            300
        )

        # Verify the adapter received the safe duration,
        # not the original 600-second request.
        self.assertEqual(
            self.adapter.commands[-1]["duration_sec"],
            300
        )

    def test_invalid_duration_rejected(self):
        # Zero duration must be rejected.
        res = self.service.trigger_actuator(
            "ZONE-A",
            duration_sec=0
        )

        self.assertFalse(res["success"])
        self.assertEqual(
            res["status"],
            "INVALID_DURATION"
        )
        self.assertEqual(
            res["relay_state"],
            "OFF"
        )

        # No relay command should have been dispatched.
        self.assertEqual(
            len(self.adapter.commands),
            0
        )

    def test_negative_duration_rejected(self):
        # Negative duration must also be rejected.
        res = self.service.trigger_actuator(
            "ZONE-A",
            duration_sec=-10
        )

        self.assertFalse(res["success"])
        self.assertEqual(
            res["status"],
            "INVALID_DURATION"
        )
        self.assertEqual(
            res["relay_state"],
            "OFF"
        )

        # No relay command should have been dispatched.
        self.assertEqual(
            len(self.adapter.commands),
            0
        )

    def test_failed_hardware_dispatch(self):
        # Simulate an ESP32/hardware adapter failure.
        failed_adapter = MockRelayAdapter(success=False)
        service = IrrigationService(adapter=failed_adapter)

        res = service.trigger_actuator(
            "ZONE-A",
            duration_sec=30
        )

        self.assertFalse(res["success"])
        self.assertEqual(
            res["status"],
            "ACTUATION_FAILED"
        )
        self.assertEqual(
            res["relay_state"],
            "OFF"
        )
        self.assertFalse(
            res["hardware_dispatched"]
        )

    def test_failed_dispatch_does_not_start_cooldown(self):
        # Simulate failed hardware dispatch.
        failed_adapter = MockRelayAdapter(success=False)
        service = IrrigationService(adapter=failed_adapter)

        res = service.trigger_actuator(
            "ZONE-A",
            duration_sec=30
        )

        self.assertFalse(res["success"])

        # Failed physical actuation must not consume
        # the 15-minute cooldown.
        status = service.get_status()

        self.assertFalse(
            status["in_cooldown"]
        )

        self.assertEqual(
            status["actuation_count"],
            0
        )

    def test_emergency_stop_dispatches_off(self):
        self.service.emergency_stop()

        # Emergency stop must send an OFF command to all zones.
        command = self.adapter.commands[-1]

        self.assertEqual(
            command["zone_id"],
            "ALL_ZONES"
        )
        self.assertEqual(
            command["state"],
            "OFF"
        )
        self.assertEqual(
            command["duration_sec"],
            0
        )

    def test_successful_actuation_dispatch(self):
        res = self.service.trigger_actuator(
            "ZONE-A",
            duration_sec=30
        )

        self.assertTrue(res["success"])
        self.assertTrue(
            res["hardware_dispatched"]
        )

        # Verify the actual command sent to the relay adapter.
        command = self.adapter.commands[-1]

        self.assertEqual(
            command["zone_id"],
            "ZONE-A"
        )
        self.assertEqual(
            command["state"],
            "ON"
        )
        self.assertEqual(
            command["duration_sec"],
            30
        )


if __name__ == "__main__":
    unittest.main()