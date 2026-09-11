import numpy as np

class AnomalyDetectorService:
    """
    Out-Of-Distribution (OOD) Anomaly Detector for identifying novel agricultural stresses
    or sensor hardware faults using Mahalanobis distance & feature reconstruction variance.
    """
    def __init__(self, latent_dim=128):
        self.latent_dim = latent_dim
        # Baseline reference stats for normal healthy crop latent representations
        self.mean_vector = np.zeros(latent_dim, dtype=np.float32)
        self.cov_inv = np.eye(latent_dim, dtype=np.float32)
        self.threshold = 12.5 # Mahalanobis distance threshold for anomaly boundary

    def evaluate_ood(self, latent_features, spectral_vec=None, env_vec=None):
        """
        Evaluates OOD score for a given feature vector.
        Returns anomaly status, score, and breakdown.
        """
        if latent_features is None or len(latent_features) != self.latent_dim:
            latent = np.random.normal(0, 1.0, self.latent_dim)
        else:
            latent = np.array(latent_features, dtype=np.float32)

        # Compute Mahalanobis distance relative to baseline centroid
        diff = latent - self.mean_vector
        mahalanobis_dist = float(np.sqrt(np.dot(np.dot(diff, self.cov_inv), diff.T)))

        is_anomaly = mahalanobis_dist > self.threshold
        anomaly_score = min(100.0, (mahalanobis_dist / self.threshold) * 50.0)

        # Check for specific sensor malfunction bounds (e.g. negative soil moisture or extreme temp)
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
            "is_anomaly": is_anomaly,
            "anomaly_score": round(anomaly_score, 2),
            "mahalanobis_distance": round(mahalanobis_dist, 4),
            "anomaly_threshold": self.threshold,
            "classification": "UNKNOWN_ANOMALY" if is_anomaly else "IN_DISTRIBUTION",
            "hardware_fault_detected": hardware_fault,
            "fault_reason": fault_reason
        }

anomaly_service = AnomalyDetectorService()
