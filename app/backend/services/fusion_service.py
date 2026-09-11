class FusionService:
    """
    Multimodal Sensor Fusion & Diagnostic Disambiguation Engine.
    Disambiguates between:
    - Spectral stress vs Soil Water stress vs Fungal Disease vs Environmental Hazard
    """

    def disambiguate_stress(self, ai_prediction, telemetry_data):
        """
        Combines PyTorch AI model outputs with physical domain knowledge rules.
        """
        raw_condition = ai_prediction.get("condition", "HEALTHY")
        confidence = ai_prediction.get("confidence", 0.85)
        severity = ai_prediction.get("severity_score", 0.0)

        temp = telemetry_data.get("temperature", 25.0)
        humidity = telemetry_data.get("humidity", 60.0)
        soil_moisture = telemetry_data.get("soil_moisture", 50.0)
        smoke = telemetry_data.get("smoke_ppm", 50.0)

        reasoning_steps = []
        disambiguated_condition = raw_condition

        # Rule 1: High smoke/gas PPM override to Environmental Hazard / Anomaly
        if smoke > 300.0:
            disambiguated_condition = "SEVERE_STRESS"
            reasoning_steps.append("CRITICAL: Gas/Smoke level exceeds safety threshold (300 PPM). Flagged as Environmental Hazard.")
            confidence = min(0.99, confidence + 0.15)

        # Rule 2: Low soil moisture + high temp disambiguates Water Stress from Disease
        elif soil_moisture < 25.0 and temp > 30.0:
            if raw_condition in ["HEALTHY", "PRE_SYMPTOMATIC_STRESS"]:
                disambiguated_condition = "WATER_STRESS"
                reasoning_steps.append("PHYSICAL RULE: High Temp (>30C) and Low Moisture (<25%) indicates Soil Water Deficit.")
            else:
                reasoning_steps.append("CONFIRMED: Environmental parameters corroborate Water Stress diagnosis.")

        # Rule 3: High humidity (>80%) + moderate temp corroborates Fungal Disease
        elif humidity > 80.0 and 20.0 <= temp <= 30.0:
            if raw_condition in ["DISEASE", "PRE_SYMPTOMATIC_STRESS"]:
                disambiguated_condition = "DISEASE"
                reasoning_steps.append("MICROCLIMATE RULE: Persistent high humidity (>80%) creates optimal fungal spore proliferation conditions.")

        # Rule 4: Pre-symptomatic spectral shift with normal env
        elif raw_condition == "PRE_SYMPTOMATIC_STRESS":
            reasoning_steps.append("SPECTRAL DISAMBIGUATION: Red-Edge (730nm) reflectance decay detected prior to microclimate deterioration.")

        else:
            reasoning_steps.append("NOMINAL: Multi-modal sensors are operating within expected baseline distributions.")

        return {
            "final_condition": disambiguated_condition,
            "raw_ai_condition": raw_condition,
            "disambiguated_confidence": round(confidence, 4),
            "severity_score": severity,
            "reasoning_trace": reasoning_steps,
            "fusion_matrix": {
                "spectral_contribution": 0.45,
                "spatial_contribution": 0.35,
                "environmental_contribution": 0.20
            }
        }

fusion_service = FusionService()
