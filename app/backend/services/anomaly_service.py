import os
import json
import numpy as np

CALIBRATION_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "checkpoints", "ood_calibration.json"))

class AnomalyDetectorService:
    """
    Out-Of-Distribution (OOD) Anomaly Detector for identifying novel crop stresses
    or sensor hardware faults using Mahalanobis distance fitted on reference baseline latent embeddings.
    """
    def __init__(self):
        self.mean_vector = None
        self.cov_inv = None
        self.threshold = None
        self.latent_dim = 128
        self.is_calibrated = False
        self._load_calibration()

    def _load_calibration(self):
        if os.path.exists(CALIBRATION_PATH):
            try:
                with open(CALIBRATION_PATH, "r") as f:
                    data = json.load(f)
                if data.get("is_calibrated", False):
                    self.mean_vector = np.array(data["mean_vector"], dtype=np.float64)
                    self.cov_inv = np.array(data["cov_inv"], dtype=np.float64)
                    self.threshold = float(data["threshold"])
                    self.latent_dim = int(data.get("latent_dim", 128))
                    self.is_calibrated = True
                    print(f"[AnomalyService] Loaded OOD calibration parameters from {CALIBRATION_PATH} (Threshold: {self.threshold:.4f})")
            except Exception as e:
                print(f"[AnomalyService] Warning: Failed to load calibration ({e}). Detector uncalibrated.")

    def evaluate_ood(self, latent_features, spectral_vec=None, env_vec=None):
        """
        Evaluates OOD status for a given feature vector using fitted Mahalanobis distance.
        NO RANDOM LATENT VECTORS ARE GENERATED. Invalid inputs raise ValueError.
        """
        if not self.is_calibrated:
            return {
                "is_calibrated": False,
                "classification": "NOT_CALIBRATED",
                "message": "OOD Detector is not calibrated. Train MM-SSNet to generate reference baseline calibration parameters.",
                "mahalanobis_distance": 0.0,
                "anomaly_score": 0.0,
                "is_anomaly": False
            }

        if latent_features is None:
            raise ValueError("[AnomalyService] latent_features cannot be None.")

        latent_arr = np.array(latent_features, dtype=np.float64)
        if latent_arr.ndim != 1 or len(latent_arr) != self.latent_dim:
            raise ValueError(f"[AnomalyService] Latent feature vector dimension mismatch. Expected ({self.latent_dim},), got {latent_arr.shape}")

        # Compute Mahalanobis distance relative to baseline centroid
        diff = latent_arr - self.mean_vector
        mahalanobis_dist = float(np.sqrt(np.dot(np.dot(diff, self.cov_inv), diff.T)))

        is_anomaly = mahalanobis_dist > self.threshold
        anomaly_score = min(100.0, (mahalanobis_dist / self.threshold) * 50.0)

        # Check physical hardware bounds
        hardware_fault = False
        fault_reason = ""
        if env_vec:
            temp, hum, soil, gas = env_vec
            if temp < -10.0 or temp > 65.0:
                hardware_fault = True
                fault_reason = "Temperature sensor reading out of physical bounds (-10C to 65C)"
            elif soil < 0.0 or soil > 100.0:
                hardware_fault = True
                fault_reason = "Soil moisture ADC voltage saturated out of 0-100% range"

        if hardware_fault:
            is_anomaly = True
            anomaly_score = 99.9

        return {
            "is_calibrated": True,
            "is_anomaly": is_anomaly,
            "anomaly_score": round(anomaly_score, 2),
            "mahalanobis_distance": round(mahalanobis_dist, 4),
            "anomaly_threshold": round(self.threshold, 4),
            "classification": "UNKNOWN_ANOMALY" if is_anomaly else "IN_DISTRIBUTION",
            "hardware_fault_detected": hardware_fault,
            "fault_reason": fault_reason
        }

anomaly_service = AnomalyDetectorService()
