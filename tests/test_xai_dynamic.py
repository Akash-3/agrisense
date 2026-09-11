import unittest
import numpy as np
from app.backend.services.xai_service import xai_service

class TestXAIDynamic(unittest.TestCase):
    def test_xai_dynamic_response_with_spatial(self):
        spec1 = [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]
        spec2 = [0.90, 0.10, 0.05, 0.05, 0.10, 0.15, 0.80, 0.85, 0.20, 0.15]

        # Two distinct RGB images
        img1 = np.ones((3, 64, 64), dtype=np.float32) * 0.1
        img2 = np.zeros((3, 64, 64), dtype=np.float32)
        img2[0, 10:30, 10:30] = 0.9
        img2[1, 20:40, 20:40] = 0.8

        res1 = xai_service.generate_xai_explanation(spec1, img1)
        res2 = xai_service.generate_xai_explanation(spec2, img2)

        self.assertEqual(res1["xai_status"], "AVAILABLE")
        self.assertEqual(res1["spatial_modality_available"], True)

        # 1. Grad-CAM heatmaps must be 64x64 matrices
        grid1 = np.array(res1["gradcam_heatmap_grid"])
        grid2 = np.array(res2["gradcam_heatmap_grid"])
        self.assertEqual(grid1.shape, (64, 64))
        self.assertEqual(grid2.shape, (64, 64))

        # REQ-6 Verification: Heatmaps from distinct images must be non-identical!
        self.assertFalse(np.array_equal(grid1, grid2), "Grad-CAM heatmaps for distinct images must not be identical!")

        # REQ-7 Verification: Spectral attributions must change dynamically with inputs!
        b1 = res1["spectral_band_importance"][0]["attribution_weight"]
        b2 = res2["spectral_band_importance"][0]["attribution_weight"]
        self.assertNotEqual(b1, b2, "Spectral band attributions for distinct inputs must not be identical!")

    def test_xai_missing_spatial(self):
        spec = [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]
        res = xai_service.generate_xai_explanation(spec, spatial_img=None)

        self.assertEqual(res["xai_status"], "UNAVAILABLE_MISSING_RGB")
        self.assertEqual(res["spatial_modality_available"], False)
        self.assertIsNone(res["gradcam_heatmap_grid"])
        self.assertIn("spectral_band_importance", res)
        self.assertEqual(len(res["spectral_band_importance"]), 10)

if __name__ == "__main__":
    unittest.main()
