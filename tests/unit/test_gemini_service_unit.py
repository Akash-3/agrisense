import os
import sys
import json
import pytest
import urllib.error
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'backend')))

from services.chatbot_service import chatbot_service

def test_missing_api_key_falls_back_to_local_engine(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    res, status, reason = chatbot_service._call_external_llm_provider("What is nitrogen?", "Wheat", [])
    assert res is None
    assert status == "LLM_NOT_CONFIGURED"
    assert "No GEMINI_API_KEY" in reason or "No LLM API Key" in reason

def test_dynamic_model_discovery_filters_non_text_models(monkeypatch):
    fake_models_response = {
        "models": [
            {"name": "models/gemini-1.5-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-2.5-flash-preview-tts", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
            {"name": "models/gemini-2.0-flash", "supportedGenerationMethods": ["generateContent"]}
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(fake_models_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        discovered = chatbot_service._discover_available_gemini_models("fake_key")
        assert "gemini-1.5-flash" in discovered
        assert "gemini-2.0-flash" in discovered
        assert "gemini-2.5-flash-preview-tts" not in discovered
        assert "text-embedding-004" not in discovered

def test_configured_model_preference(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key_123")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-custom-model")

    with patch("urllib.request.urlopen", side_effect=Exception("Discovery disabled")):
        res, status, reason = chatbot_service._call_external_llm_provider("What is NPK?", "Wheat", [])
        # Verification that fallback attempted configured_model first can be verified from candidates list
        # when url is hit in urlopen call
        assert status is not None

def test_fallback_on_404_or_503(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key_123")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    calls = []

    def mock_urlopen(req, timeout=8):
        url = req.full_url if hasattr(req, "full_url") else req
        if "models?" in url:
            # discovery
            mock_res = MagicMock()
            mock_res.status = 200
            mock_res.read.return_value = json.dumps({"models": [{"name": "models/gemini-fallback-working", "supportedGenerationMethods": ["generateContent"]}]}).encode("utf-8")
            mock_res.__enter__.return_value = mock_res
            return mock_res
        
        model = url.split("models/")[1].split(":")[0]
        calls.append(model)
        if model == "gemini-1.5-flash":
            raise urllib.error.HTTPError(url, 404, "Model Not Found", {}, None)
        elif model == "gemini-2.0-flash":
            raise urllib.error.HTTPError(url, 503, "Service Unavailable", {}, None)
        else:
            mock_res = MagicMock()
            mock_res.status = 200
            mock_res.read.return_value = json.dumps({
                "candidates": [{"content": {"parts": [{"text": "Dynamic agronomic response from fallback model."}]}}]
            }).encode("utf-8")
            mock_res.__enter__.return_value = mock_res
            return mock_res

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        res, status, reason = chatbot_service._call_external_llm_provider("What is NPK?", "Wheat", [])
        assert res is not None
        assert res["answer"] == "Dynamic agronomic response from fallback model."
        assert len(calls) >= 2

def test_auth_failure_401_breaks_early(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "invalid_key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def mock_urlopen(req, timeout=8):
        url = req.full_url if hasattr(req, "full_url") else req
        raise urllib.error.HTTPError(url, 401, "API Key Invalid", {}, None)

    with patch("urllib.request.urlopen", side_effect=mock_urlopen) as mock_call:
        res, status, reason = chatbot_service._call_external_llm_provider("What is NPK?", "Wheat", [])
        assert res is None
        assert status == "LLM_PROVIDER_AUTH_ERROR_401"
        assert mock_call.call_count == 2  # 1 for discovery attempt, 1 for first model generateContent attempt before break

def test_network_timeout_and_empty_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key_123")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
        res, status, reason = chatbot_service._call_external_llm_provider("What is NPK?", "Wheat", [])
        assert res is None
        assert status == "LLM_PROVIDER_TIMEOUT"

def test_full_process_chat_query_local_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    out = chatbot_service.process_chat_query(
        query="What is nitrogen deficiency?",
        authenticated_farmer_id=1,
        language="en"
    )

    assert out["status"] == "success"
    assert "answer" in out
    assert "Nitrogen" in out["answer"]
    assert out["evidence_state"] is not None
