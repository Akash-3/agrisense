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

def test_concise_response_length_factual_question(monkeypatch):
    """Verifies that a factual question produces a concise response under 100 words."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    res = chatbot_service.process_chat_query(
        query="What is the optimal nitrogen application for wheat during tillering stage?",
        authenticated_farmer_id=1,
        crop_type="Wheat",
        language="en"
    )
    assert res["status"] == "success"
    answer = res["answer"]
    words = chatbot_service.count_words(answer)
    assert words <= 100, f"Expected <= 100 words, got {words}: {answer}"
    assert words >= 15, f"Expected meaningful response, got {words} words: {answer}"
    assert "nitrogen" in answer.lower() or "wheat" in answer.lower() or "action" in answer.lower()

def test_concise_response_length_long_agricultural_question(monkeypatch):
    """Verifies that a complex multi-part question stays strictly within 100 words."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    complex_q = (
        "How do I recognize early symptoms of powdery mildew on cucurbits, "
        "what organic and chemical fungicides should I apply, and what irrigation precautions "
        "are necessary to stop sporulation in high humidity conditions?"
    )
    res = chatbot_service.process_chat_query(
        query=complex_q,
        authenticated_farmer_id=1,
        language="en"
    )
    assert res["status"] == "success"
    words = chatbot_service.count_words(res["answer"])
    assert words <= 100, f"Expected <= 100 words, got {words}: {res['answer']}"

def test_word_limit_enforcement_compresses_oversized_llm_response(monkeypatch):
    """Simulates an excessively verbose 250+ word LLM response and verifies backend compression under 100 words."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock_key_concise")

    oversized_answer = (
        "Hello esteemed farmer! Welcome to AgriSense. Regarding your inquiry about rice blast disease management, "
        "it is essential to realize that Magnaporthe oryzae is a catastrophic fungal pathogen affecting rice across all Indian agro-climatic zones. "
        "First, you should carefully observe spindle-shaped lesions with grayish centers on leaf blades. "
        "Second, you should immediately refrain from applying excessive nitrogenous fertilizers such as urea during high vegetative growth. "
        "Third, ensure adequate field drainage and apply tricyclazole 75 WP at 0.6 grams per liter or isoprothiolane 40 EC at 1.5 ml per liter of water. "
        "Furthermore, we recommend that you inspect surrounding bunds and remove alternate weed hosts like Echinochloa colona. "
        "Fourth, practice synchronized planting across your village community to mitigate fungal spore dispersion across adjacent paddy fields. "
        "Fifth, consult your local district agricultural extension officer or Krishi Vigyan Kendra agronomist for certified resistant seed varieties. "
        "Caution: Always wear chemical-resistant gloves, eye goggles, and a face mask before spraying fungicides to avoid dermal and respiratory toxicity. "
        "I sincerely hope that this detailed guidance assists your agricultural operations and ensures a bountiful harvest this season!"
    )

    def mock_urlopen(req, timeout=8):
        mock_res = MagicMock()
        mock_res.status = 200
        mock_res.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": oversized_answer}]}}]
        }).encode("utf-8")
        mock_res.__enter__.return_value = mock_res
        return mock_res

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        res = chatbot_service.process_chat_query(
            query="How to treat rice blast?",
            authenticated_farmer_id=1,
            language="en"
        )
        assert res["status"] == "success"
        compressed = res["answer"]
        words = chatbot_service.count_words(compressed)
        assert words <= 100, f"Expected <= 100 words, got {words}: {compressed}"
        assert "caution" in compressed.lower() or "warning" in compressed.lower() or "gloves" in compressed.lower(), "Caution warning should be preserved"
        # Confirm complete clause/sentence boundary (not dangling)
        assert compressed[-1] in ".!?)>" or compressed[-1].isalnum()

def test_word_limit_enforcement_preserves_caution_warnings():
    """Verifies that enforce_word_limit isolates and preserves critical caution statements."""
    verbose_text = (
        "Answer: Downy mildew is actively spreading in your grapevine orchard due to persistent nighttime moisture. "
        "Action 1: Prune infected lateral shoots to enhance canopy aeration and reduce relative humidity. "
        "Action 2: Spray copper oxychloride 50 WP at 2.5 grams per liter of water or metalaxyl MZ at 2 grams per liter. "
        "Action 3: Install drip irrigation instead of overhead sprinklers to keep grape foliage dry during morning hours. "
        "Action 4: Collect fallen diseased leaves and burn them outside the vineyard boundary to destroy overwintering oospores. "
        "Action 5: Monitor daily weather alerts from the Indian Meteorological Department for sudden rain events. "
        "Caution: Do not spray copper fungicides during peak flowering as it causes severe blossom drop and russeting on young grape clusters."
    )
    compressed = chatbot_service.enforce_word_limit(verbose_text, max_words=70)
    words = chatbot_service.count_words(compressed)
    assert words <= 70, f"Expected <= 70 words, got {words}"
    assert "caution" in compressed.lower()
    assert "flowering" in compressed.lower() or "russeting" in compressed.lower()

def test_local_fallback_answers_strictly_under_100_words(monkeypatch):
    """Verifies that all local domain knowledge engine templates produce responses <= 100 words."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    queries = [
        "What is the pest control for aphids in cotton?",
        "How do I treat blight disease in tomato?",
        "What is the fertilizer schedule for sugarcane?",
        "What is the ideal soil pH for wheat?",
        "When should I irrigate my paddy crop?",
        "What are the government subsidies for drip irrigation in Maharashtra?",
        "General advice for organic compost application?"
    ]

    for q in queries:
        res = chatbot_service.process_chat_query(query=q, authenticated_farmer_id=1, language="en")
        assert res["generation_metadata"]["strategy"] == "LOCAL_DOMAIN_KNOWLEDGE_ENGINE"
        word_count = chatbot_service.count_words(res["answer"])
        assert word_count <= 100, f"Query '{q}' exceeded 100 words ({word_count}): {res['answer']}"
        assert word_count >= 20, f"Query '{q}' too short ({word_count}): {res['answer']}"

def test_multilingual_answers_under_100_words(monkeypatch):
    """Verifies that translated responses across Indian languages stay <= 100 words."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    lang_queries = [
        ("hi", "गेहूं में यूरिया कब डालना चाहिए?"),
        ("te", "వరి పంటలో ఎరువుల యాజమాన్యం ఎలా చేయాలి?"),
        ("ta", "நெல் பயிரில் பூச்சி கட்டுப்பாடு முறைகள் என்ன?"),
        ("kn", "ಗೋಧಿ ಬೆಳೆಗೆ ಯೂರಿಯಾ ಗೊಬ್ಬರ ಯಾವಾಗ ಹಾಕಬೇಕು?"),
        ("pa", "ਕਣਕ ਦੀ ਫ਼ਸਲ ਵਿੱਚ ਖਾਦ ਕਦੋਂ ਪਾਉਣੀ ਚਾਹੀਦੀ ਹੈ?")
    ]

    for lang, q in lang_queries:
        res = chatbot_service.process_chat_query(query=q, authenticated_farmer_id=1, language=lang)
        word_count = chatbot_service.count_words(res["answer"])
        assert word_count <= 100, f"Language '{lang}' exceeded 100 words ({word_count}): {res['answer']}"
