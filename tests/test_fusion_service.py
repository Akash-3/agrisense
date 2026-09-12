import unittest

from app.backend.services.fusion_service import fusion_service


class TestFusionService(unittest.TestCase):

    def test_healthy_no_action(self):
        ai_prediction = {
            "condition": "HEALTHY",
            "confidence": 0.90,
            "severity_score": 10.0
        }

        telemetry = {
            "temperature": 25.0,
            "humidity": 60.0,
            "soil_moisture": 50.0,
            "smoke_ppm": 80.0
        }

        result = fusion_service.disambiguate_stress(
            ai_prediction,
            telemetry
        )

        self.assertEqual(result["final_condition"], "HEALTHY")
        self.assertEqual(result["recommended_action"], "NO_ACTION")
        self.assertEqual(result["rule_type"], "EXPERT_RULE_WEIGHTS")

    def test_pre_symptomatic_monitor(self):
        ai_prediction = {
            "condition": "PRE_SYMPTOMATIC_STRESS",
            "confidence": 0.80,
            "severity_score": 30.0
        }

        telemetry = {
            "temperature": 25.0,
            "humidity": 60.0,
            "soil_moisture": 50.0,
            "smoke_ppm": 80.0
        }

        result = fusion_service.disambiguate_stress(
            ai_prediction,
            telemetry
        )

        self.assertEqual(
            result["final_condition"],
            "PRE_SYMPTOMATIC_STRESS"
        )
        self.assertEqual(result["recommended_action"], "MONITOR")

    def test_water_stress_irrigate(self):
        ai_prediction = {
            "condition": "HEALTHY",
            "confidence": 0.90,
            "severity_score": 20.0
        }

        telemetry = {
            "temperature": 35.0,
            "humidity": 50.0,
            "soil_moisture": 20.0,
            "smoke_ppm": 80.0
        }

        result = fusion_service.disambiguate_stress(
            ai_prediction,
            telemetry
        )

        self.assertEqual(result["final_condition"], "WATER_STRESS")
        self.assertEqual(result["recommended_action"], "IRRIGATE")

    def test_disease_high_humidity_revisit(self):
        ai_prediction = {
            "condition": "DISEASE",
            "confidence": 0.85,
            "severity_score": 55.0
        }

        telemetry = {
            "temperature": 25.0,
            "humidity": 90.0,
            "soil_moisture": 50.0,
            "smoke_ppm": 80.0
        }

        result = fusion_service.disambiguate_stress(
            ai_prediction,
            telemetry
        )

        self.assertEqual(result["final_condition"], "DISEASE")
        self.assertEqual(result["recommended_action"], "REVISIT")

    def test_high_smoke_manual_inspection(self):
        ai_prediction = {
            "condition": "HEALTHY",
            "confidence": 0.90,
            "severity_score": 15.0
        }

        telemetry = {
            "temperature": 25.0,
            "humidity": 60.0,
            "soil_moisture": 50.0,
            "smoke_ppm": 350.0
        }

        result = fusion_service.disambiguate_stress(
            ai_prediction,
            telemetry
        )

        self.assertEqual(result["final_condition"], "SEVERE_STRESS")
        self.assertEqual(
            result["recommended_action"],
            "MANUAL_INSPECTION"
        )


if __name__ == "__main__":
    unittest.main()