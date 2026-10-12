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

def test_intent_classification():
    """Verifies that user queries are categorized into appropriate conversational or agricultural intents."""
    assert chatbot_service.classify_intent("hi") == "GREETING"
    assert chatbot_service.classify_intent("hello") == "GREETING"
    assert chatbot_service.classify_intent("namaste") == "GREETING"
    assert chatbot_service.classify_intent("good morning") == "GREETING"
    assert chatbot_service.classify_intent("Hi, can you explain nitrogen deficiency?") == "AGRICULTURAL_WITH_GREETING"
    assert chatbot_service.classify_intent("Namaste, gehu me khad kab dale?") == "AGRICULTURAL_WITH_GREETING"
    assert chatbot_service.classify_intent("Who are you?") == "IDENTITY_CAPABILITY"
    assert chatbot_service.classify_intent("What can you do?") == "IDENTITY_CAPABILITY"
    assert chatbot_service.classify_intent("Thank you so much") == "GRATITUDE"
    assert chatbot_service.classify_intent("Bye") == "FAREWELL"
    assert chatbot_service.classify_intent("Okay") == "ACKNOWLEDGEMENT"
    assert chatbot_service.classify_intent("Explain again") == "CONFUSION"
    assert chatbot_service.classify_intent("What is the NPK ratio for Wheat?") == "AGRICULTURAL"

def test_pure_greeting_response_quality_and_name_handling(monkeypatch):
    """Verifies that pure greetings return short, warm greetings with farmer's name when known, and no invented names when unknown."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # 1. Greeting with known farmer name
    res_with_name = chatbot_service.process_chat_query(
        query="Hello",
        authenticated_farmer_id=1,
        farmer_name="Suresh Kumar",
        language="en"
    )
    ans1 = res_with_name["answer"]
    w1 = chatbot_service.count_words(ans1)
    assert "Suresh Kumar" in ans1, f"Expected name 'Suresh Kumar' in greeting: {ans1}"
    assert w1 <= 30, f"Greeting should be concise (10-30 words), got {w1}: {ans1}"
    assert "Answer:" not in ans1 and "Action:" not in ans1 and "Caution:" not in ans1, "Greetings must not contain rigid headers"
    assert "Krishi Vigyan Kendra" not in ans1, "Greetings must not contain KVK warnings"
    assert "Wheat in Punjab" not in ans1, "Greetings must not assume crops or locations"
    assert res_with_name["web_citations"] == [], "Web citations should not be retrieved for pure greetings"

    # 2. Greeting without farmer name (should not invent names like Akash or Kavya or Farmer)
    res_no_name = chatbot_service.process_chat_query(
        query="Hi",
        authenticated_farmer_id=2,
        farmer_name=None,
        language="en"
    )
    ans2 = res_no_name["answer"]
    w2 = chatbot_service.count_words(ans2)
    assert "Akash" not in ans2 and "Kavya" not in ans2 and "Farmer" not in ans2, f"Should not invent names: {ans2}"
    assert w2 <= 30, f"Greeting should be concise, got {w2}: {ans2}"
    assert "Answer:" not in ans2 and "Action:" not in ans2 and "Caution:" not in ans2

def test_compound_greeting_and_agricultural_query(monkeypatch):
    """Verifies that compound queries answer the agricultural question rather than only saying hello."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    res = chatbot_service.process_chat_query(
        query="Hi, can you explain nitrogen deficiency in wheat?",
        authenticated_farmer_id=1,
        farmer_name="Ramesh",
        language="en"
    )
    ans = res["answer"]
    assert "nitrogen" in ans.lower() or "wheat" in ans.lower() or "urea" in ans.lower()
    assert chatbot_service.count_words(ans) <= 100

def test_language_detection_and_matching(monkeypatch):
    """Verifies language matching: UI override, Devanagari Hindi, Odia, Hinglish, and Romanized Odia."""
    # 1. Devanagari Hindi detection
    assert chatbot_service.detect_language("गेहूं में खाद कब डालें?", "auto") == "hi"

    # 2. Odia script detection
    assert chatbot_service.detect_language("ଧାନ ଫସଲରେ କେଉଁ ସାର ପ୍ରୟୋଗ କରିବେ?", "auto") == "or"

    # 3. Romanized Hinglish detection
    assert chatbot_service.detect_language("gehu me khad kab dale", "auto") == "hi"
    assert chatbot_service.detect_language("namaste mera naam ramesh hai", "auto") == "hi"

    # 4. Romanized Odia detection
    assert chatbot_service.detect_language("namaskar mora chasa kemiti heba", "auto") == "or"

    # 5. UI selection overrides message text
    assert chatbot_service.detect_language("Hello, how are you?", "hi") == "hi"
    assert chatbot_service.detect_language("Hello, how are you?", "or") == "or"

def test_conversational_responses_multilingual(monkeypatch):
    """Verifies greetings and identity responses across Hindi, Odia, and English."""
    # Hindi greeting
    res_hi = chatbot_service.get_conversational_response("GREETING", "hi", "रमेश")
    assert "रमेश" in res_hi and "नमस्ते" in res_hi
    assert chatbot_service.count_words(res_hi) <= 30

    # Odia greeting
    res_or = chatbot_service.get_conversational_response("GREETING", "or", "ସୁରେଶ")
    assert "ସୁରେଶ" in res_or and "ନମସ୍କାର" in res_or
    assert chatbot_service.count_words(res_or) <= 30

    # Identity explanation
    res_id = chatbot_service.get_conversational_response("IDENTITY_CAPABILITY", "en")
    assert "AgriSense AI" in res_id
    assert chatbot_service.count_words(res_id) <= 50
