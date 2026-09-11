import unittest
from app.backend.services.mission_service import mission_service

class TestMissionValidation(unittest.TestCase):
    def test_missing_boundary_raises_error(self):
        # Empty boundary list must raise ValueError
        with self.assertRaises(ValueError):
            mission_service.generate_lawnmower_pattern([])

    def test_valid_boundary_generates_simulated_waypoints(self):
        boundary = [
            {"lat": 28.6135, "lng": 77.2085},
            {"lat": 28.6145, "lng": 77.2085},
            {"lat": 28.6145, "lng": 77.2095},
            {"lat": 28.6135, "lng": 77.2095}
        ]
        res = mission_service.generate_lawnmower_pattern(boundary)
        self.assertEqual(res["execution_mode"], "SIMULATED_WAYPOINTS")
        self.assertEqual(res["mavlink_connection_status"], "NOT_CONNECTED (SIMULATION)")
        self.assertGreater(len(res["waypoints"]), 3)

if __name__ == "__main__":
    unittest.main()
