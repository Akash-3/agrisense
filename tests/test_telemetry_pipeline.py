import os
import sys
import unittest
from unittest.mock import patch

# Ensure app/backend directory is in sys.path for backend dependencies
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient
from main import app

class TestTelemetryPipelineIngest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_esp32_telemetry_ingest_pipeline(self):
        """
        REQ-9 Verification: Hardware telemetry ingestion must invoke AIService & MM-SSNet.
        Must NOT invoke simulator.compute_mm_ssnet_inference for hardware.
        """
        payload = {
            "device_id": "ESP32-HARDWARE-01",
            "soil_moisture": 45.5,
            "temperature": 28.2,
            "humidity": 62.0,
            "smoke_ppm": 85.0,
            "spectral": [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]
        }
        with patch(
            "routers.telemetry.simulator.compute_mm_ssnet_inference",
            side_effect=AssertionError(
            "Hardware telemetry incorrectly invoked simulator inference"
            ),
            ):
                res = self.client.post("/api/v1/telemetry/ingest", json=payload)
        self.assertEqual(res.status_code, 200)

        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["pipeline"], "REAL_TELEMETRY_PIPELINE")
        self.assertIn("ai_diagnosis", data)

        diag = data["ai_diagnosis"]
        self.assertTrue(diag["is_real_ai"])
        self.assertEqual(
            diag["pipeline"],
            "REAL_ESP32 -> PYTORCH_MMSSNET -> FUSION -> OOD -> WEBSOCKET"
        )
        self.assertEqual(diag["model_version"], "MM-SSNet-v2.0-PyTorch")

        # Verify the fusion result is actually propagated to the API response
        self.assertIn("recommended_action", diag)
        self.assertIn(
            diag["recommended_action"],
            [
                "NO_ACTION",
                "MONITOR",
                "REVISIT",
                "IRRIGATE",
                "MANUAL_INSPECTION",
            ],
        )
        self.assertEqual(diag["rule_type"], "EXPERT_RULE_WEIGHTS")

if __name__ == "__main__":
    unittest.main()
