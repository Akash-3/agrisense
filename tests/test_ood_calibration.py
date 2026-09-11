import unittest
import numpy as np
from app.backend.services.anomaly_service import anomaly_service

class TestOODCalibration(unittest.TestCase):
    def test_calibrated_detector(self):
        # 1. Verify detector calibration parameters
        self.assertTrue(anomaly_service.is_calibrated)
        self.assertIsNotNone(anomaly_service.mean_vector)
        self.assertIsNotNone(anomaly_service.cov_inv)
        self.assertIsNotNone(anomaly_service.threshold)

        # 2. Evaluate normal sample
        normal_latent = anomaly_service.mean_vector.tolist()
        res = anomaly_service.evaluate_ood(normal_latent)
        self.assertEqual(res["is_anomaly"], False)
        self.assertEqual(res["classification"], "IN_DISTRIBUTION")

        # 3. Evaluate outlier sample
        outlier_latent = (anomaly_service.mean_vector + 10.0 * np.ones_like(anomaly_service.mean_vector)).tolist()
        res_out = anomaly_service.evaluate_ood(outlier_latent)
        self.assertEqual(res_out["is_anomaly"], True)
        self.assertEqual(res_out["classification"], "UNKNOWN_ANOMALY")

    def test_invalid_input_rejection(self):
        # Must raise ValueError on invalid vector shape
        with self.assertRaises(ValueError):
            anomaly_service.evaluate_ood([1.0, 2.0])

if __name__ == "__main__":
    unittest.main()
