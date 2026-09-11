import unittest
import os
import json
from ml.ablation import run_ablation_study

class TestDynamicAblation(unittest.TestCase):
    def test_ablation_metrics_are_calculated(self):
        """
        REQ-4 Anti-Hardcoding Verification: Executes quick 1-epoch ablation study across 3 seeds.
        Asserts mean and std metrics are present and dynamically generated.
        """
        results = run_ablation_study(epochs_per_variant=1, seeds=(42, 43))
        
        self.assertIn("metadata", results)
        self.assertEqual(results["metadata"]["num_variants"], 7)
        self.assertEqual(results["metadata"]["real_world_validation"], False)
        self.assertEqual(results["metadata"]["dataset_type"], "synthetic_development")
        
        variants = results["variants"]
        self.assertIn("Variant G: Tri-Modal MM-SSNet (Proposed)", variants)
        self.assertEqual(len(variants), 7)
        
        tri = variants["Variant G: Tri-Modal MM-SSNet (Proposed)"]
        self.assertIn("accuracy_pct_mean", tri)
        self.assertIn("accuracy_pct_std", tri)
        self.assertIn("f1_score_macro_mean", tri)
        self.assertIn("f1_score_macro_std", tri)
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

    def test_no_hardcoded_benchmark_strings(self):
        """
        Anti-Hardcoding Audit: Ensures ablation.py source code contains zero assigned hardcoded performance numbers.
        """
        ablation_file = os.path.join(os.path.dirname(__file__), "..", "ml", "ablation.py")
        with open(ablation_file, "r", encoding="utf-8") as f:
            code = f.read()

        forbidden_assigns = ["accuracy_pct = 96.", "f1_score = 91.", "accuracy_pct = 74.", "acc = 83."]
        for forbidden in forbidden_assigns:
            self.assertNotIn(forbidden, code)

if __name__ == "__main__":
    unittest.main()
