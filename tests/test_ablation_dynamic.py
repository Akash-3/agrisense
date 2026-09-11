import unittest
import os
import json
from ml.ablation import run_ablation_study

class TestDynamicAblation(unittest.TestCase):
    def test_ablation_metrics_are_calculated(self):
        # Run 1-epoch quick ablation study across 7 variants
        results = run_ablation_study(epochs_per_variant=1)
        
        self.assertIn("metadata", results)
        self.assertEqual(results["metadata"]["num_variants"], 7)
        self.assertEqual(results["metadata"]["real_world_validation"], False)
        
        variants = results["variants"]
        self.assertIn("Variant G: Tri-Modal MM-SSNet (Proposed)", variants)
        self.assertEqual(len(variants), 7)
        
        tri = variants["Variant G: Tri-Modal MM-SSNet (Proposed)"]
        self.assertIn("accuracy_pct", tri)
        self.assertIn("f1_score_macro", tri)
        self.assertIn("f1_score_weighted", tri)
        self.assertIn("confusion_matrix", tri)
        self.assertIn("evaluation_dataset", tri)
        self.assertEqual(tri["synthetic_development"], True)
        self.assertEqual(tri["real_world_validation"], False)

        # Check report file exists and is valid JSON
        report_path = os.path.join(os.path.dirname(__file__), "..", "ml", "results", "ablation_report.json")
        self.assertTrue(os.path.exists(report_path))
        with open(report_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["metadata"]["num_variants"], 7)

if __name__ == "__main__":
    unittest.main()
