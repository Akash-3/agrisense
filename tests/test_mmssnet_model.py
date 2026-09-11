import unittest
import torch
import numpy as np
from ml.model import MMSSNet
from ml.dataset import generate_synthetic_multimodal_data

class TestMMSSNetModel(unittest.TestCase):
    def setUp(self):
        self.model = MMSSNet(num_classes=6)

    def test_forward_pass_shapes(self):
        spec = torch.randn(4, 10)
        spat = torch.randn(4, 3, 64, 64)
        env = torch.randn(4, 4)

        out = self.model(spec, spat, env)

        self.assertEqual(out["class_logits"].shape, (4, 6))
        self.assertEqual(out["severity"].shape, (4,))
        self.assertEqual(out["lead_time"].shape, (4,))
        self.assertEqual(out["latent_features"].shape, (4, 128))
        self.assertEqual(out["spatial_modality_available"], True)

    def test_missing_spatial_modality(self):
        spec = torch.randn(4, 10)
        env = torch.randn(4, 4)

        out = self.model(spec, None, env)

        self.assertEqual(out["class_logits"].shape, (4, 6))
        self.assertEqual(out["spatial_modality_available"], False)

    def test_synthetic_generator(self):
        spec, spat, env, labels, sevs, leads, masks = generate_synthetic_multimodal_data(num_samples=60)
        self.assertEqual(len(spec), 60)
        self.assertEqual(spec.shape[1], 10)
        self.assertEqual(spat.shape[1:], (3, 64, 64))
        self.assertEqual(env.shape[1], 4)
        self.assertEqual(len(masks), 60)

if __name__ == "__main__":
    unittest.main()
