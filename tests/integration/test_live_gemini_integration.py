import os
import sys
import unittest
import pytest

# Ensure app/backend and repo_root are on path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_path = os.path.join(repo_root, "app", "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from services.chatbot_service import ProductionAgriculturalChatbotService

class TestLiveGeminiIntegration(unittest.TestCase):
    def setUp(self):
        self.service = ProductionAgriculturalChatbotService()
        self.gemini_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()

    def test_live_gemini_api_call(self):
        """
        Executes an unmocked live HTTP request to Google Gemini API if a valid API key is present.
        If no API key is set, explicitly skips the test and logs that live verification is incomplete.
        """
        if not self.gemini_key:
            self.skipTest("LIVE VERIFICATION INCOMPLETE: Neither GEMINI_API_KEY nor GOOGLE_API_KEY is configured in environment.")

        prompt = "Explain the difference between nitrogen deficiency and iron deficiency in plants in three numbered points."
        
        # Real HTTP API request without mocking
        res = self.service.process_chat_query(
            query=prompt,
            authenticated_farmer_id=1,
            location="Punjab",
            crop_type="Wheat"
        )
        
        meta = res.get("generation_metadata", {})
        
        # 1. Verify Strategy and Provider
        self.assertEqual(meta.get("strategy"), "LLM_GENERATIVE_AI", f"Expected LLM_GENERATIVE_AI strategy but got {meta.get('strategy')}. Reason: {meta.get('provider_failure_reason')}")
        self.assertEqual(meta.get("provider"), "Google Gemini")
        self.assertEqual(meta.get("provider_status"), "SUCCESS")
        
        # 2. Verify Model and Latency
        configured_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        self.assertTrue(len(meta.get("model", "")) > 0)
        self.assertGreater(meta.get("provider_latency_ms", 0), 0)
        
        # 3. Verify Response Text Quality
        answer = res.get("answer", "")
        self.assertIn("1", answer, "Answer should contain numbered point 1")
        self.assertIn("2", answer, "Answer should contain numbered point 2")
        self.assertIn("3", answer, "Answer should contain numbered point 3")
        self.assertTrue(
            "nitrogen" in answer.lower() or "chlorosis" in answer.lower(),
            "Answer should address nitrogen/iron deficiency concepts"
        )
        print(f"\n[LIVE GEMINI SUCCESS] Provider: {meta['provider']} | Model: {meta['model']} | Latency: {meta['provider_latency_ms']}ms")

if __name__ == "__main__":
    unittest.main()
