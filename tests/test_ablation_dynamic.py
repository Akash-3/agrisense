import unittest
import os
import json
from ml.ablation import run_ablation_study

class TestDynamicAblation(unittest.TestCase):
    def test_ablation_metrics_are_calculated(self):
        # Run 1-epoch quick ablation study
        results = run_ablation_study(epochs_per_variant=1)
        self.assertIn("Tri-Modal MM-SSNet (Proposed)", results)
        
        tri = results["Tri-Modal MM-SSNet (Proposed)"]
        self.assertIn("accuracy_pct", tri)
        self.assertIn("f1_score", tri)
        self.assertIn("evaluation_dataset", tri)
        self.assertEqual(tri["is_synthetic_evaluation"], True)

        # Check report file exists and is valid JSON
        report_path = os.path.join(os.path.dirname(__file__), "..", "ml", "results", "ablation_report.json")
        self.assertTrue(os.path.exists(report_path))
        with open(report_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["Tri-Modal MM-SSNet (Proposed)"]["evaluation_dataset"], "SYNTHETIC_DEVELOPMENT_DATASET")

if __name__ == "__main__":
    unittest.main()
