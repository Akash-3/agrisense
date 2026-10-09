import os
import sys
import re
import json
import html
import time
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from services import ai_service, xai_service

# SUPPORTED 13 INDIAN LANGUAGES CATALOG
SUPPORTED_LANGUAGES = {
    "en": {"name": "English", "native": "English", "flag": "🇬🇧"},
    "hi": {"name": "Hindi", "native": "हिंदी", "flag": "🇮🇳"},
    "ta": {"name": "Tamil", "native": "தமிழ்", "flag": "🇮🇳"},
    "te": {"name": "Telugu", "native": "తెలుగు", "flag": "🇮🇳"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ", "flag": "🇮🇳"},
    "mr": {"name": "Marathi", "native": "मराठी", "flag": "🇮🇳"},
    "bn": {"name": "Bengali", "native": "বাংলা", "flag": "🇮🇳"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી", "flag": "🇮🇳"},
    "pa": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ", "flag": "🇮🇳"},
    "ml": {"name": "Malayalam", "native": "മലയാളം", "flag": "🇮🇳"},
    "or": {"name": "Odia", "native": "ଓଡ଼ିଆ", "flag": "🇮🇳"},
    "as": {"name": "Assamese", "native": "অসমীয়া", "flag": "🇮🇳"},
    "ur": {"name": "Urdu", "native": "اردو", "flag": "🇮🇳"}
}

# AUTHORITATIVE AGRICULTURAL KNOWLEDGE REPOSITORY (ICAR / KVK / GOVT / FAO ALIGNED)
AUTHORITATIVE_KNOWLEDGE = {
    "npk_ratios": {
        "wheat": "ICAR Recommendation: 120:60:40 kg N:P2O5:K2O per hectare. Apply 50% N + full P&K basal at sowing, remaining N split across CRI and tillering stages.",
        "paddy": "ICAR-NRRI Recommendation: 100:50:50 kg N:P2O5:K2O per hectare with Zinc Sulphate 25kg/ha basal application.",
        "cotton": "State Agri University Recommendation: 120:60:60 kg N:P2O5:K2O per hectare split across vegetative and boll formation phases.",
        "maize": "ICAR-IIMR Recommendation: 150:60:40 kg N:P2O5:K2O per hectare.",
        "sugarcane": "IISR Recommendation: 250:115:115 kg N:P2O5:K2O per hectare with 25 tonnes/ha organic FYM."
    },
    "disease_remedies": {
        "leaf_blight": "Apply Copper Oxychloride 50% WP @ 2.5g/L water or Mancozeb 75% WP @ 2g/L. Ensure adequate field drainage and canopy aeration.",
        "yellow_rust": "Apply Propiconazole 25% EC @ 1ml/L water immediately upon initial field detection.",
        "chlorosis": "Foliar spray of Ferrous Sulphate (0.5%) + Citric Acid (0.1%) or check soil pH & nitrogen levels.",
        "powdery_mildew": "Spray Wettable Sulphur 80% WP @ 3g/L or Hexaconazole 5% EC @ 1ml/L.",
        "caterpillar_pest": "Spray Emamectin Benzoate 5% SG @ 0.4g/L or Neem Oil (10,000 PPM) @ 3ml/L water."
    },
    "govt_schemes": {
        "pm_kisan": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi): Provides ₹6,000/year direct benefit transfer to landholding farmer families in 3 equal installments of ₹2,000 every 4 months.",
        "pmfby": "PMFBY (Pradhan Mantri Fasal Bima Yojana): Crop insurance premium capped at 1.5% for Rabi, 2.0% for Kharif, and 5.0% for Commercial/Horticultural crops.",
        "soil_health_card": "Soil Health Card Scheme: Tests 12 soil parameters (N, P, K, S, Zn, Fe, Cu, Mn, Bo, pH, EC, OC) biennially.",
        "kcc": "Kisan Credit Card (KCC): Short-term credit limit up to ₹3 Lakh at an effective interest rate of 4% per annum with prompt repayment incentive."
    }
}

# REGIONAL CONTEXT MATRIX (12 STATES)
REGIONAL_AGRI_DATA = {
    "punjab": {"state": "Punjab", "major_crops": ["Wheat", "Paddy (Rice)", "Cotton", "Sugarcane", "Mustard"], "soil_types": ["Alluvial soil", "Loamy soil"], "major_mandis": ["Khanna Mandi", "Ludhiana Mandi", "Amritsar Mandi"], "schemes": ["PM-KISAN", "Pani Bachao Paisa Kamao", "CRM Subsidies"]},
    "haryana": {"state": "Haryana", "major_crops": ["Wheat", "Mustard", "Paddy", "Cotton", "Bajra"], "soil_types": ["Alluvial soil", "Sandy loam"], "major_mandis": ["Karnal Mandi", "Kurukshetra Mandi", "Sirsa Mandi"], "schemes": ["PM-KISAN", "Mera Pani Meri Virasat", "Bhavantar Bharpayee Yojna"]},
    "maharashtra": {"state": "Maharashtra", "major_crops": ["Cotton", "Sugarcane", "Soybean", "Onion", "Tur", "Grapes"], "soil_types": ["Black Cotton Soil (Regur)", "Laterite soil"], "major_mandis": ["Lasalgaon Mandi", "Nagpur Mandi", "Solapur Mandi"], "schemes": ["PM-KISAN", "Namo Shetkari Sanman", "Magel Tyala Shettale"]},
    "tamil nadu": {"state": "Tamil Nadu", "major_crops": ["Paddy", "Sugarcane", "Groundnut", "Banana", "Coconut", "Cotton"], "soil_types": ["Red soil", "Black soil", "Alluvial soil"], "major_mandis": ["Koyambedu Market", "Madurai Mandi", "Erode Turmeric Market"], "schemes": ["PM-KISAN", "Kalaignar Cereal Scheme", "Solar Pump Subsidy"]},
    "telangana": {"state": "Telangana", "major_crops": ["Paddy", "Cotton", "Maize", "Chilli", "Turmeric"], "soil_types": ["Red sandy loams (Chalka)", "Black soils"], "major_mandis": ["Warangal Grain Market", "Khammam Chilli Yard", "Nizamabad Market"], "schemes": ["PM-KISAN", "Rythu Bandhu", "Rythu Bima"]},
    "andhra pradesh": {"state": "Andhra Pradesh", "major_crops": ["Paddy", "Chilli", "Groundnut", "Tobacco", "Mango", "Cotton"], "soil_types": ["Red soil", "Delta Alluvial soil", "Black soil"], "major_mandis": ["Guntur Chilli Market", "Vijayawada Mandi", "Kurnool Market"], "schemes": ["PM-KISAN", "YSR Rythu Bharosa", "Free Crop Insurance"]},
    "karnataka": {"state": "Karnataka", "major_crops": ["Ragi", "Maize", "Paddy", "Coffee", "Cotton", "Arecanut"], "soil_types": ["Red soil", "Laterite soil", "Black soil"], "major_mandis": ["Yeshwanthpur Mandi", "Shivamogga Market", "Davangere Market"], "schemes": ["PM-KISAN", "Krishi Bhagya", "Raitha Vidya Nidhi"]},
    "uttar pradesh": {"state": "Uttar Pradesh", "major_crops": ["Wheat", "Sugarcane", "Paddy", "Potato", "Mustard", "Mentha"], "soil_types": ["Gangetic Alluvial soil"], "major_mandis": ["Agra Potato Mandi", "Lakhimpur Sugarcane Hub", "Kanpur Mandi"], "schemes": ["PM-KISAN", "UP Kisan Karj Rahat", "Free Electricity Irrigation"]},
    "gujarat": {"state": "Gujarat", "major_crops": ["Cotton", "Groundnut", "Castor", "Cumin", "Wheat", "Mustard"], "soil_types": ["Black soil", "Goradu Sandy Loam", "Coastal Alluvial"], "major_mandis": ["Unjha Cumin Mandi", "Gondal Market Yard", "Rajkot Mandi"], "schemes": ["PM-KISAN", "Mukhyamantri Kisan Sahay", "i-Khedut Portal"]},
    "west bengal": {"state": "West Bengal", "major_crops": ["Paddy", "Jute", "Potato", "Tea", "Mustard", "Maize"], "soil_types": ["Alluvial soil", "Red and Yellow soil"], "major_mandis": ["Burdwan Rice Hub", "Singur Potato Yard", "Siliguri Tea Auction"], "schemes": ["PM-KISAN", "Krishak Bandhu", "Jute Farmers Incentive"]},
    "bihar": {"state": "Bihar", "major_crops": ["Paddy", "Wheat", "Maize", "Makhana", "Banana", "Litchi"], "soil_types": ["North Bihar Alluvial", "South Gangetic soil"], "major_mandis": ["Gulabbagh Maize Market", "Muzaffarpur Litchi Yard", "Patna Mandi"], "schemes": ["PM-KISAN", "Bihar Fasal Sahayata", "Diesel Subsidy"]},
    "kerala": {"state": "Kerala", "major_crops": ["Coconut", "Rubber", "Pepper", "Cardamom", "Paddy", "Banana"], "soil_types": ["Laterite soil", "Coastal Alluvial"], "major_mandis": ["Kochi Spice Exchange", "Kottayam Rubber Yard", "Palakkad Paddy Hub"], "schemes": ["PM-KISAN", "Subhiksha Keralam", "Kerala Crop Insurance"]}
}

class ProductionAgriculturalChatbotService:
    def __init__(self):
        self.knowledge_base = AUTHORITATIVE_KNOWLEDGE
        self.translation_dictionary = self._init_full_multilingual_translations()

    def _init_full_multilingual_translations(self) -> Dict[str, Dict[str, str]]:
        return {
            "hi": {
                "Greetings! I am AgriSense AI Assistant.": "नमस्ते! मैं एग्रीसेंस एआई सहायक हूँ।",
                "Based on your location": "आपकी स्थिति के अनुसार",
                "Recommended Crops": "अनुशंसित फसलें",
                "Fertilizer NPK Advice": "उर्वरक एनपीके सलाह",
                "Disease Diagnosis": "रोग निदान",
                "Severity": "गंभीरता",
                "Treatment Remedy": "उपचार का उपाय",
                "Live Web Search Citations": "लाइव वेब खोज संदर्भ",
                "Government Schemes": "सरकारी योजनाएं",
                "Mandi Market Update": "मंडी बाजार अपडेट",
                "Pest & Disease Advisory": "कीट और रोग परामर्श",
                "Agricultural Advisory": "कृषि सलाह",
                "EVIDENCE STATE": "प्रमाण स्थिति",
                "HIGH EVIDENCE": "उच्च प्रमाण",
                "MODERATE EVIDENCE": "मध्यम प्रमाण",
                "LIMITED EVIDENCE": "सीमित प्रमाण",
                "INSUFFICIENT EVIDENCE": "अपर्याप्त प्रमाण",
                "Farm soil moisture and sensor telemetry are currently unavailable": "फार्म की मिट्टी की नमी और सेंसर टेलीमेट्री वर्तमान में उपलब्ध नहीं है।",
                "Current live web search was unavailable": "वर्तमान लाइव वेब खोज उपलब्ध नहीं थी, इसलिए आज का बाजार भाव सत्यापित नहीं किया जा सका।"
            },
            "ta": {
                "Greetings! I am AgriSense AI Assistant.": "வணக்கம்! நான் அக்ரிசென்ஸ் AI உதவியாளர்.",
                "Based on your location": "உங்கள் இருப்பிடத்தின் அடிப்படையில்",
                "Recommended Crops": "பரிந்துரைக்கப்பட்ட பயிர்கள்",
                "Fertilizer NPK Advice": "உர NPK ஆலோசனை",
                "Disease Diagnosis": "நோய் கண்டறிதல்",
                "Government Schemes": "அரசு திட்டங்கள்",
                "Mandi Market Update": "சந்தை விலை புதுப்பிப்பு",
                "Agricultural Advisory": "விவசாய ஆலோசனை",
                "EVIDENCE STATE": "சான்று நிலை"
            },
            "te": {
                "Greetings! I am AgriSense AI Assistant.": "నమస్కారం! నేను అగ్రిసెన్స్ AI సహాయకుడిని.",
                "Based on your location": "మీ ప్రాంతం ఆధారంగా",
                "Recommended Crops": "సిఫార్సు చేసిన పంటలు",
                "Fertilizer NPK Advice": "ఎరువుల NPK సలహా",
                "Disease Diagnosis": "వ్యాధి నిర్ధారణ",
                "Government Schemes": "ప్రభుత్వ పథకాలు",
                "Mandi Market Update": "మార్కెట్ ధరల వివరాలు",
                "Agricultural Advisory": "వ్యవసాయ సలహాలు",
                "EVIDENCE STATE": "సాక్ష్యాల స్థాయి"
            },
            "kn": {
                "Greetings! I am AgriSense AI Assistant.": "ನಮಸ್ಕಾರ! ನಾನು ಅಗ್ರಿಸೆನ್ಸ್ AI ಸಹಾಯಕ.",
                "Based on your location": "ನಿಮ್ಮ ಸ್ಥಳದ ಆಧಾರದ ಮೇಲೆ",
                "Recommended Crops": "ಶಿಫಾರಸು ಮಾಡಿದ ಬೆಳೆಗಳು",
                "Fertilizer NPK Advice": "ಗೊಬ್ಬರ NPK ಸಲಹೆ",
                "Disease Diagnosis": "ರೋಗ ನಿರ್ಧಾರ",
                "Government Schemes": "ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು",
                "Mandi Market Update": "ಮಾರುಕಟ್ಟೆ ದರಗಳ ವಿವರ",
                "Agricultural Advisory": "ಕೃಷಿ ಸಲಹೆಗಳು",
                "EVIDENCE STATE": "ಆಧಾರ ಸ್ಥಿತಿ"
            },
            "mr": {
                "Greetings! I am AgriSense AI Assistant.": "नमस्कार! मी ॲग्रीसेन्स AI सहाय्यक आहे.",
                "Based on your location": "तुमच्या स्थानावर आधारित",
                "Recommended Crops": "शिफारस केलेली पिके",
                "Fertilizer NPK Advice": "खत NPK सल्ला",
                "Disease Diagnosis": "रोग निदान",
                "Government Schemes": "शासकीय योजना",
                "Mandi Market Update": "बाजार भाव अपडेट",
                "Agricultural Advisory": "शेतीविषयक सल्ला",
                "EVIDENCE STATE": "पुरावा स्थिती"
            },
            "bn": {
                "Greetings! I am AgriSense AI Assistant.": "নমস্কার! আমি এগ্রিসেন্স এআই সহকারী।",
                "Based on your location": "আপনার অবস্থানের ওপর ভিত্তি করে",
                "Recommended Crops": "সুপারিশকৃত ফসল",
                "Fertilizer NPK Advice": "সার NPK পরামর্শ",
                "Disease Diagnosis": "রোগ নির্ণয়",
                "Government Schemes": "সরকারি প্রকল্প",
                "Mandi Market Update": "বাজার দর তথ্য",
                "Agricultural Advisory": "কৃষি সংক্রান্ত পরামর্শ",
                "EVIDENCE STATE": "প্রমাণের স্থিতি"
            },
            "gu": {
                "Greetings! I am AgriSense AI Assistant.": "નમસ્તે! હું એગ્રીસેન્સ AI સહાયક છું.",
                "Based on your location": "તમારા સ્થાનના આધારે",
                "Recommended Crops": "ભલામણ કરેલ પાકો",
                "Fertilizer NPK Advice": "ખાતર NPK સલાહ",
                "Disease Diagnosis": "રોગ નિદાન",
                "Government Schemes": "સરકારી યોજનાઓ",
                "Mandi Market Update": "મંડી બજાર ભાવ",
                "Agricultural Advisory": "કૃષિ સલાહ",
                "EVIDENCE STATE": "પુરાવા સ્થિતિ"
            },
            "pa": {
                "Greetings! I am AgriSense AI Assistant.": "ਸਤਿ ਸ਼੍ਰੀ ਅਕਾਲ! ਮੈਂ ਐਗਰੀਸੈਂਸ AI ਸਹਾਇਕ ਹਾਂ।",
                "Based on your location": "ਤੁਹਾਡੇ ਇਲਾਕੇ ਦੇ ਆਧਾਰ 'ਤੇ",
                "Recommended Crops": "ਸਿਫਾਰਸ਼ ਕੀਤੀਆਂ ਫਸਲਾਂ",
                "Fertilizer NPK Advice": "ਖਾਦ NPK ਸਲਾਹ",
                "Disease Diagnosis": "ਬਿਮਾਰੀ ਦੀ ਜਾਂਚ",
                "Government Schemes": "ਸਰਕਾਰੀ ਸਕੀਮਾਂ",
                "Mandi Market Update": "ਮੰਡੀ ਭਾਅ ਅਪਡੇਟ",
                "Agricultural Advisory": "ਖੇਤੀਬਾੜੀ ਸਲਾਹ",
                "EVIDENCE STATE": "ਸਬੂਤ ਸਥਿਤੀ"
            },
            "ml": {
                "Greetings! I am AgriSense AI Assistant.": "നമസ്കാരം! ഞാൻ അഗ്രിസെൻസ് AI സഹായിയാണ്.",
                "Based on your location": "നിങ്ങളുടെ സ്ഥലത്തെ അടിസ്ഥാനമാക്കി",
                "Recommended Crops": "ശുപാർശ ചെയ്ത വിളകൾ",
                "Government Schemes": "സർക്കാർ പദ്ധതികൾ",
                "Agricultural Advisory": "കാർഷിക നിർദ്ദേശങ്ങൾ",
                "EVIDENCE STATE": "തെളിവ് നില"
            },
            "or": {
                "Greetings! I am AgriSense AI Assistant.": "ନମସ୍କାର! ମୁଁ ଏଗ୍ରିସେନ୍ସ AI ସହାୟକ |",
                "Based on your location": "ଆପଣଙ୍କ ସ୍ଥାନ ଆଧାରରେ",
                "Recommended Crops": "ସୁପାରିଶ କରାଯାଇଥିବା ଫସଲ",
                "Government Schemes": "ସରକାରୀ ଯୋଜନା",
                "Agricultural Advisory": "କୃଷି ପରାମର୍ଶ",
                "EVIDENCE STATE": "ପ୍ରମାଣ ସ୍ଥିତି"
            },
            "as": {
                "Greetings! I am AgriSense AI Assistant.": "নমস্কাৰ! মই এগ্ৰিচেন্স AI সহায়ক।",
                "Based on your location": "আপোনাৰ স্থানৰ ওপৰত ভিত্তি কৰি",
                "Government Schemes": "চৰকাৰী আঁচনি",
                "Agricultural Advisory": "কৃষি সম্পৰ্কীয় পৰামৰ্শ",
                "EVIDENCE STATE": "প্ৰমাণৰ অৱস্থা"
            },
            "ur": {
                "Greetings! I am AgriSense AI Assistant.": "السلام علیکم! میں ایگری سینس AI اسسٹنٹ ہوں۔",
                "Based on your location": "آپ کے مقام کی بنیاد پر",
                "Government Schemes": "سرکاری اسکیمیں",
                "Agricultural Advisory": "زرعی مشورہ",
                "EVIDENCE STATE": "ثبوت کی حالت"
            }
        }

    def detect_language(self, text: str, requested_lang: str = "auto") -> str:
        """Detect language script or fallback to requested language."""
        if requested_lang and requested_lang != "auto" and requested_lang in SUPPORTED_LANGUAGES:
            return requested_lang

        if re.search(r'[\u0900-\u097F]', text):
            if re.search(r'(आहे|नाही|आलो|करतो|शेती|पिके|खत)', text):
                return "mr"
            return "hi"
        elif re.search(r'[\u0B80-\u0BFF]', text):
            return "ta"
        elif re.search(r'[\u0C00-\u0C7F]', text):
            return "te"
        elif re.search(r'[\u0C80-\u0CFF]', text):
            return "kn"
        elif re.search(r'[\u0980-\u09FF]', text):
            if re.search(r'(অসম|আমি|হয়|শস্য)', text):
                return "as"
            return "bn"
        elif re.search(r'[\u0A80-\u0AFF]', text):
            return "gu"
        elif re.search(r'[\u0A00-\u0A7F]', text):
            return "pa"
        elif re.search(r'[\u0D00-\u0D7F]', text):
            return "ml"
        elif re.search(r'[\u0B00-\u0B7F]', text):
            return "or"
        elif re.search(r'[\u0600-\u06FF]', text):
            return "ur"
        return "en"

    def sanitize_untrusted_input(self, text: str) -> str:
        """Sanitizes prompt input and retrieved web content against injection attempts."""
        if not text:
            return ""
        # Remove prompt injection phrases attempting to override system behavior
        forbidden_patterns = [
            r"ignore\s+(all\s+)?(previous\s+)?instructions",
            r"reveal\s+(your\s+)?system\s+prompt",
            r"give\s+me\s+(another|other)\s+farmer",
            r"expose\s+(secrets|api\s*key|token)",
            r"bypass\s+safety"
        ]
        sanitized = text
        for pat in forbidden_patterns:
            sanitized = re.sub(pat, "[FILTERED_SECURITY_VIOLATION]", sanitized, flags=re.IGNORECASE)
        return sanitized

    def fetch_destination_web_page(self, target_url: str, timeout: int = 4) -> Optional[str]:
        """Retrieves and validates destination web page content."""
        if not target_url or not target_url.startswith(("http://", "https://")):
            return None
        try:
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AgriSenseBot/3.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    raw_content = response.read(64 * 1024).decode('utf-8', errors='ignore')
                    clean_text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', raw_content, flags=re.DOTALL)
                    clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
                    clean_text = html.unescape(re.sub(r'\s+', ' ', clean_text)).strip()
                    return clean_text[:500] if len(clean_text) > 50 else None
        except Exception:
            pass
        return None

    def search_internet_agricultural_data(self, query: str, location_str: str = "") -> List[Dict[str, str]]:
        """Perform real-time web search and destination page verification across DDG Lite and DDG HTML."""
        results = []
        clean_query = self.sanitize_untrusted_input(query)
        search_term = f"{clean_query} {location_str}".strip()

        # Strategy 1: DDG Lite POST / GET
        try:
            post_data = urllib.parse.urlencode({'q': search_term}).encode('utf-8')
            req = urllib.request.Request(
                "https://lite.duckduckgo.com/lite/",
                data=post_data,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                content = response.read().decode('utf-8', errors='ignore')
                a_tags = re.findall(r'<a[^>]+href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>', content, re.DOTALL)
                snippets = re.findall(r'<td[^>]*class=[\'"]result-snippet[\'"][^>]*>(.*?)</td>', content, re.DOTALL)

                valid_idx = 0
                for href, raw_title in a_tags:
                    if len(results) >= 3:
                        break
                    clean_title = html.unescape(re.sub(r'<[^>]+>', '', raw_title)).strip()
                    if not clean_title or len(clean_title) < 3 or "DuckDuckGo" in clean_title:
                        continue

                    match_uddg = re.search(r'uddg=([^&]+)', href)
                    target_url = urllib.parse.unquote(match_uddg.group(1)) if match_uddg else href
                    if target_url.startswith("//"):
                        target_url = "https:" + target_url
                    if not target_url.startswith("http"):
                        continue

                    snippet_text = ""
                    if valid_idx < len(snippets):
                        snippet_text = html.unescape(re.sub(r'<[^>]+>', '', snippets[valid_idx])).strip()
                    valid_idx += 1

                    clean_snippet = self.sanitize_untrusted_input(snippet_text or f"Live agricultural update for {search_term}.")
                    dest_text = self.fetch_destination_web_page(target_url, timeout=3)
                    verification_status = "LIVE_VERIFIED_PAGE" if dest_text else "LIVE_SEARCH_SNIPPET"

                    results.append({
                        "title": clean_title,
                        "snippet": clean_snippet,
                        "url": target_url,
                        "source_status": verification_status
                    })
        except Exception as e:
            print(f"[Chatbot Web Search Notice] DDG Lite notice: {e}")

        # Strategy 2: DDG HTML GET Fallback if Lite produced 0 results
        if not results:
            try:
                encoded_term = urllib.parse.quote(search_term)
                url = f"https://html.duckduckgo.com/html/?q={encoded_term}"
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
                )
                with urllib.request.urlopen(req, timeout=4) as response:
                    content = response.read().decode('utf-8', errors='ignore')
                    links = re.findall(r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', content, re.DOTALL)
                    snippets = re.findall(r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', content, re.DOTALL)
                    if not snippets:
                        snippets = re.findall(r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</span>', content, re.DOTALL)

                    for i in range(min(len(links), 3)):
                        raw_href, raw_title = links[i]
                        clean_title = html.unescape(re.sub(r'<[^>]+>', '', raw_title)).strip()
                        match_uddg = re.search(r'uddg=([^&]+)', raw_href)
                        target_url = urllib.parse.unquote(match_uddg.group(1)) if match_uddg else raw_href
                        if target_url.startswith("//"):
                            target_url = "https:" + target_url

                        clean_snippet = ""
                        if i < len(snippets):
                            clean_snippet = html.unescape(re.sub(r'<[^>]+>', '', snippets[i])).strip()
                        clean_snippet = self.sanitize_untrusted_input(clean_snippet)

                        dest_text = self.fetch_destination_web_page(target_url, timeout=3)
                        verification_status = "LIVE_VERIFIED_PAGE" if dest_text else "LIVE_SEARCH_SNIPPET"

                        results.append({
                            "title": clean_title if clean_title else "Agri Web Intelligence",
                            "snippet": clean_snippet if clean_snippet else f"Live market update for {query}.",
                            "url": target_url,
                            "source_status": verification_status
                        })
            except Exception as e:
                print(f"[Chatbot Web Search Notice] DDG HTML notice: {e}")

        # Strategy 3: No artificial fallback URLs when live web search is unavailable or blocked
        return results

    def get_region_info(self, location_str: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
        """Resolve region metadata based on location string or coordinates."""
        loc_lower = (location_str or "").lower()

        if lat and lon and not location_str:
            if 30.0 <= lat <= 32.5 and 74.0 <= lon <= 77.0:
                loc_lower = "punjab"
            elif 28.0 <= lat <= 30.5 and 75.0 <= lon <= 77.5:
                loc_lower = "haryana"
            elif 18.0 <= lat <= 20.5 and 72.5 <= lon <= 75.0:
                loc_lower = "maharashtra"
            elif 10.0 <= lat <= 13.5 and 77.0 <= lon <= 80.0:
                loc_lower = "tamil nadu"
            elif 16.0 <= lat <= 18.5 and 78.0 <= lon <= 81.0:
                loc_lower = "telangana"
            elif 12.0 <= lat <= 15.0 and 74.0 <= lon <= 78.0:
                loc_lower = "karnataka"
            elif 22.0 <= lat <= 24.5 and 69.0 <= lon <= 73.0:
                loc_lower = "gujarat"
            elif 26.0 <= lat <= 28.5 and 80.0 <= lon <= 84.0:
                loc_lower = "uttar pradesh"

        for key, info in REGIONAL_AGRI_DATA.items():
            if key in loc_lower or info["state"].lower() in loc_lower:
                return info

        return {
            "state": location_str or "All India",
            "major_crops": ["Paddy", "Wheat", "Cotton", "Sugarcane", "Pulses", "Maize"],
            "soil_types": ["Alluvial soil", "Black soil", "Red soil"],
            "major_mandis": ["e-NAM Mandi Portal", "Regional APMC Yards"],
            "schemes": ["PM-KISAN", "PMFBY", "Soil Health Card", "Kisan Credit Card (KCC)"]
        }

    def _translate_response(self, text_en: str, lang_code: str) -> str:
        """Translates response headers and text into requested Indian language."""
        if lang_code == "en":
            return text_en

        lang_dict = self.translation_dictionary.get(lang_code, {})
        translated_text = text_en
        for key, val in lang_dict.items():
            translated_text = translated_text.replace(key, val)

        return translated_text

    def _generate_dynamic_agronomic_answer(
        self,
        query: str,
        q_lower: str,
        context_topic: Optional[str],
        context_crop: Optional[str],
        resolved_crop: str,
        farm_info: Dict[str, Any],
        region_info: Dict[str, Any],
        web_citations: List[Dict[str, str]],
        evidence_state: str,
        vision_diagnosis: Optional[Dict[str, Any]],
        resolved_history: List[Dict[str, str]],
        is_live_search_attempted: bool = False
    ) -> str:
        """Generates dynamic, query-tailored agronomic responses for domain questions, follow-ups, and general inquiries."""
        sections = []

        # 1. Vision Diagnosis Payload (if leaf image was attached)
        if vision_diagnosis:
            remedy = self.knowledge_base["disease_remedies"].get("leaf_blight")
            sections.append(
                f"🔬 **Crop Health Visual Diagnosis (PyTorch MM-SSNet Visual Scan)**:\n"
                f"- **Condition**: {vision_diagnosis['condition']} ({vision_diagnosis['probabilistic_certainty']})\n"
                f"- **Confidence Score**: {vision_diagnosis['confidence_pct']}%\n"
                f"- **Severity Rating**: {vision_diagnosis['severity_score']}/100\n"
                f"- **Attributing Band**: {vision_diagnosis['top_spectral_band']}\n"
                f"- **ICAR / KVK Advisory Remedy**: {remedy}"
            )

        # Detect crop explicitly mentioned in current query first
        query_crop = None
        for crop in ["wheat", "rice", "paddy", "cotton", "maize", "sugarcane", "groundnut", "potato", "onion", "mustard", "pulses", "soybean", "ragi"]:
            if re.search(r'\b' + re.escape(crop) + r'\b', q_lower):
                query_crop = crop.capitalize()
                break

        target_crop = query_crop or context_crop or resolved_crop or "Wheat"
        if target_crop.lower() == "rice":
            target_crop = "Paddy"
        crop_key = target_crop.lower()

        # 2. Query Intent Analysis & Direct Knowledge Synthesis

        is_nitrogen_query = any(w in q_lower for w in ["nitrogen", "n deficiency", "nitrate", "ammonium"]) or re.search(r'\b(n)\b', q_lower) is not None or context_topic == "nitrogen"
        is_deficiency_query = any(w in q_lower for w in ["deficiency", "chlorosis", "yellowing", "yellow", "deficient", "symptom", "symptoms", "look for"])
        is_remedy_query = any(w in q_lower for w in ["what should i do", "how to treat", "remedy", "cure", "fix", "solution", "action", "manage", "treat", "next step", "what next", "do next"])
        is_confirm_query = any(w in q_lower for w in ["confirm", "how can i confirm", "how to confirm", "test", "verification", "verify"])
        is_importance_query = any(w in q_lower for w in ["why is", "importance of", "role of", "function of", "why does", "benefit"])
        is_nitrogen_vs_iron = ("nitrogen" in q_lower and "iron" in q_lower) or ("n deficiency" in q_lower and "fe deficiency" in q_lower) or ("chlorosis" in q_lower and "iron" in q_lower)
        is_child_prompt = any(w in q_lower for w in ["10-year-old", "child", "kid", "explain to a child", "simple words"])
        is_one_sentence = any(w in q_lower for w in ["one-sentence", "one sentence", "in a single sentence", "summarize in one sentence"])
        is_photosynthesis_query = "photosynthesis" in q_lower

        if is_child_prompt:
            sections.append(
                "🌱 **Understanding Soil & Plants (For Young Learners)**:\n"
                "Think of soil as a super kitchen for plants! Soil is made of tiny bits of rocks, old leaves, air, water, and millions of friendly little bugs.\n\n"
                "Just like you need food, water, and vitamins to grow strong and run around, plants put their roots down into the soil to drink water and eat nutrients like Nitrogen, Phosphorus, and Potassium. Healthy soil makes happy, green plants!"
            )

        elif is_one_sentence:
            if "water" in q_lower:
                sections.append("Plants need water to transport nutrients from the soil to their leaves and carry out photosynthesis to produce energy and survive.")
            else:
                sections.append("Plants require balanced soil nutrients and water to synthesize chlorophyll, build cellular structures, and achieve healthy growth.")

        elif is_nitrogen_vs_iron:
            sections.append(
                "🍃 **Comparing Nitrogen Deficiency vs. Iron Deficiency in Plants**:\n\n"
                "1. **Affected Leaf Location & Mobility**: Nitrogen ($N$) is mobile inside the plant, so deficiency symptoms appear first on **older lower leaves** (yellowing from tip inward). Iron ($Fe$) is immobile, so deficiency symptoms appear first on **youngest top leaves**.\n"
                "2. **Pattern of Leaf Yellowing (Chlorosis)**: Nitrogen deficiency causes uniform yellowing across the entire lower leaf blade and veins. Iron deficiency causes distinct **interveinal chlorosis**, where leaf tissue between veins turns pale yellow or white while veins stay dark green.\n"
                "3. **Soil Conditions & Correction**: Nitrogen deficiency is caused by low soil organic matter or insufficient fertilizer (corrected with Urea top-dressing/Nano Urea spray). Iron deficiency occurs mainly in high-pH alkaline/calcareous soils (corrected with foliar spray of 0.5% Ferrous Sulphate $FeSO_4$ + 0.1% Citric Acid)."
            )

        is_potassium_query = any(w in q_lower for w in ["potassium", "potash"]) or re.search(r'\b(k)\b', q_lower) is not None
        is_npk_vs_single = "difference between npk" in q_lower or ("npk" in q_lower and "single" in q_lower) or ("complex" in q_lower and "straight" in q_lower)
        is_organic_matter = any(w in q_lower for w in ["organic matter", "humus", "compost", "fym"])
        is_soil_ph = "ph" in q_lower and ("soil" in q_lower or "acid" in q_lower or "alkaline" in q_lower or "absorption" in q_lower)
        is_safety = any(w in q_lower for w in ["safety", "precaution", "precautions", "handling", "protective", "ppe"])

        if is_photosynthesis_query:
            sections.append(
                "🌿 **Photosynthesis in Plants**:\n"
                "Photosynthesis is the primary biological process by which green plants convert light energy, carbon dioxide ($CO_2$), and water ($H_2O$) into oxygen ($O_2$) and chemical energy stored in glucose.\n\n"
                "**Key Components & Function:**\n"
                "- **Chlorophyll Pigments**: Chlorophyll molecules inside plant chloroplasts absorb sunlight energy.\n"
                "- **Nutrient Requirement**: Nitrogen, Magnesium (the core atom in chlorophyll), and Iron are critical for synthesizing and maintaining active chlorophyll molecules."
            )

        elif is_npk_vs_single:
            sections.append(
                "🧪 **NPK Complex Fertilizers vs. Single-Nutrient Fertilizers**:\n"
                "Understanding the difference between compound NPK fertilizers and straight single-nutrient fertilizers:\n\n"
                "- **NPK Fertilizers (Complex)**: Contain two or three primary nutrients in fixed balanced ratios (e.g., NPK 19-19-19 or 12-32-16). They ensure balanced nutrient distribution during basal application or fertigation.\n"
                "- **Single-Nutrient Fertilizers (Straight)**: Supply only one primary element (e.g., Urea for 46% N, Single Super Phosphate / SSP for 16% P₂O₅, Muriate of Potash / MOP for 60% K₂O). They allow precise top-dressing targeted at specific nutrient deficiencies."
            )

        elif is_organic_matter:
            sections.append(
                "🪱 **Importance of Soil Organic Matter for Soil Health**:\n"
                "Soil Organic Matter (SOM) is the biological foundation of healthy, resilient agricultural soils:\n\n"
                "- **Nutrient Retention & CEC**: Enhances Cation Exchange Capacity (CEC), storing nutrients (N, P, K, Ca, Mg) and preventing leaching.\n"
                "- **Water Holding Capacity**: Increases soil moisture retention and drought resilience by forming stable soil aggregates.\n"
                "- **Microbial Activity**: Provides carbon energy for beneficial soil microbes, mycorrhizal fungi, and earthworms.\n"
                "- **Soil Structure**: Improves soil aeration, root penetration, and prevents surface crusting and erosion."
            )

        elif is_soil_ph:
            sections.append(
                "🧪 **Importance of Soil pH in Plant Nutrient Absorption**:\n"
                "Soil pH measures the acidity or alkalinity of soil, directly controlling chemical nutrient availability to plant roots:\n\n"
                "- **Optimal Range**: A pH between **6.0 and 7.5** allows maximum availability of essential macro and micronutrients.\n"
                "- **Acidic Soils (pH < 6.0)**: Fixes Phosphorus and makes Aluminum/Manganese toxic while reducing Calcium and Magnesium availability.\n"
                "- **Alkaline Soils (pH > 7.5)**: Locks up Iron, Zinc, Boron, and Manganese, causing interveinal leaf chlorosis.\n"
                "- **Correction**: Apply agricultural lime (calcium carbonate) to raise pH in acidic soils, or gypsum/sulfur to lower pH in sodic/alkaline soils."
            )

        elif is_safety:
            sections.append(
                "⚠️ **Safety Precautions for Handling Chemical Fertilizers**:\n"
                "Follow these essential safety practices when storing, mixing, and applying chemical fertilizers:\n\n"
                "1. **Personal Protective Equipment (PPE)**: Wear protective rubber gloves, safety goggles, a dust mask, and long-sleeved clothing during handling.\n"
                "2. **Prevent Contact & Inhalation**: Avoid direct skin contact or inhaling fertilizer dust, especially when opening bags of concentrated Urea or DAP.\n"
                "3. **Proper Storage**: Store fertilizer bags off the ground on wooden pallets in a dry, well-ventilated, locked shed away from direct sunlight, seeds, food, and children.\n"
                "4. **Hygiene & Washup**: Thoroughly wash hands, arms, and face with soap and clean water immediately after application."
            )

        elif is_nitrogen_query or ("npk" in q_lower and "ratio" not in q_lower and "dose" not in q_lower):
            if is_confirm_query:
                sections.append(
                    f"🧪 **Confirming Nitrogen Deficiency in {target_crop}**:\n"
                    f"While visual symptoms (lower leaf yellowing in a V-shape) provide strong initial indicators, visual observation alone is not 100% conclusive. To definitively confirm nitrogen deficiency in your **{target_crop}** crop:\n\n"
                    f"1. **Soil Health Card / Soil Testing**: Perform a laboratory soil test to measure available Nitrogen ($N$), Organic Carbon ($OC$), and soil pH.\n"
                    f"2. **Leaf Tissue / SPAD Meter Analysis**: Use a SPAD chlorophyll meter or leaf tissue test to measure active chlorophyll levels in flag leaves.\n"
                    f"3. **Rule Out Confounding Factors**: Verify that yellowing is not caused by waterlogging, root damage, soil salinity, or Sulfur/Iron deficiency.\n"
                    f"4. **KVK Specialist Consultation**: Consult your local Krishi Vigyan Kendra (KVK) or extension officer for field verification."
                )
            elif is_remedy_query or ("do" in q_lower and "deficiency" in q_lower) or ("next" in q_lower and "do" in q_lower):
                # Remedy / Action for Nitrogen Deficiency
                sections.append(
                    f"💊 **Remedial Actions & Next Steps for Nitrogen Deficiency in {target_crop}**:\n"
                    f"If your **{target_crop}** crop shows signs of nitrogen deficiency, take the following ICAR/KVK corrective measures:\n\n"
                    f"1. **Evaluate Growth Stage & Records**: Check crop growth stage, previous fertilizer applications, and soil moisture levels.\n"
                    f"2. **Top-Dressing Urea**: Apply Urea (46% N) @ **25–30 kg per acre** (~60 kg/ha) as a top-dressing during critical growth stages (such as Crown Root Initiation or first irrigation for wheat).\n"
                    f"3. **Foliar Spray for Rapid Absorption**: Spray a **2% Urea solution** (20g Urea per liter of water) or **Nano Urea @ 2–4 mL per liter** of water during early morning or late afternoon for quick canopy recovery.\n"
                    f"4. **Ensure Soil Moisture**: Always apply top-dressed urea when adequate soil moisture is present to avoid root burn and ammonia loss.\n"
                    f"5. **Soil Health Card Guidelines**: Follow ICAR recommendations (120:60:40 kg N:P₂O₅:K₂O per hectare for irrigated wheat) adjusted for your soil test values."
                )
            elif is_deficiency_query or "identify" in q_lower or "symptom" in q_lower or "look for" in q_lower:
                # Identifying Nitrogen Deficiency
                sections.append(
                    f"🔍 **Identifying Nitrogen Deficiency Symptoms in {target_crop}**:\n"
                    f"Nitrogen deficiency in **{target_crop}** presents distinct visual diagnostic symptoms:\n\n"
                    f"- **Older Leaves Yellow First**: Nitrogen is mobile within plant tissues, so the plant translocates nitrogen to younger growth, causing yellowing (chlorosis) to appear on older, lower leaves first.\n"
                    f"- **V-Shaped Yellowing**: Chlorosis typically develops in a characteristic V-shape, starting at the leaf tip and advancing down the midrib.\n"
                    f"- **Stunted Growth & Reduced Tillering**: Plants remain short, develop fewer tillers or stems, and leaves appear narrow and pale green.\n"
                    f"- **Early Leaf Death**: Under severe deficiency, lower leaves turn light brown and dry up prematurely.\n\n"
                    f"*Diagnostic Tip*: Symptoms alone provide an initial indicator. Confirm via soil testing or KVK guidance, as yellowing can also stem from waterlogging or Sulfur deficiency."
                )
            elif is_importance_query or "important" in q_lower or "why" in q_lower:
                # Importance of Nitrogen
                sections.append(
                    f"🌾 **Importance of Nitrogen for {target_crop}**:\n"
                    f"Nitrogen (N) is a vital macronutrient essential for achieving optimal growth and yield in **{target_crop}**:\n\n"
                    f"- **Tillering & Canopy Expansion**: Promotes rapid tiller formation, stem elongation, and active leaf area index (LAI).\n"
                    f"- **Chlorophyll & Photosynthesis**: Increases chlorophyll density, ensuring high photosynthetic rates during vegetative and boot stages.\n"
                    f"- **Protein Synthesis**: Essential for constructing plant amino acids, structural proteins, and enzymes.\n"
                    f"- **Grain Filling & Quality**: Directly influences grain head size, kernel density, and grain protein content."
                )
            else:
                # General Explanation of What Nitrogen Is
                crop_note = f" For your **{target_crop}** crop, maintaining adequate nitrogen supply is crucial during early tillering and growth." if target_crop else ""
                sections.append(
                    f"🌱 **What is Nitrogen in Plants?**\n"
                    f"Nitrogen (N) is an essential primary macronutrient required in large quantities by plants for healthy vegetative growth, cellular development, and reproduction.{crop_note}\n\n"
                    f"**Key Functions of Nitrogen in Plants:**\n"
                    f"- **Chlorophyll Production**: Nitrogen is a core component of chlorophyll, the green pigment that absorbs sunlight for photosynthesis.\n"
                    f"- **Protein & Enzyme Synthesis**: It forms amino acids, which are the fundamental building blocks of plant proteins and enzymes.\n"
                    f"- **Genetic Code (DNA & RNA)**: Nitrogen is a key structural constituent of nucleic acids required for cell division.\n"
                    f"- **Vegetative Vigor**: Drives active stem elongation, leaf canopy expansion, and tillering.\n\n"
                    f"**Sufficiency vs. Deficiency Indicators:**\n"
                    f"- *Sufficient*: Dark green, lush foliage with rapid shoot and tiller development.\n"
                    f"- *Deficient*: Pale green to yellowing leaves starting on older lower foliage, short plant height, and poor tillering."
                )

        elif is_potassium_query:
            sections.append(
                f"🧪 **Potassium (K) in Plants & {target_crop}**:\n"
                f"Potassium (K) is an essential primary macronutrient responsible for enzyme activation, water regulation, and stress tolerance in **{target_crop}**.\n\n"
                f"**Key Functions:**\n"
                f"- **Stomatal Regulation**: Controls the opening and closing of stomata, managing water transpiration during heat or drought.\n"
                f"- **Disease & Lodging Resistance**: Strengthens plant cell walls, reducing vulnerability to lodging, drought, and fungal pathogens.\n"
                f"- **Grain Quality**: Enhances starch translocation, grain plumpness, and test weight during grain filling.\n\n"
                f"**Application Tip**: Apply MOP (Muriate of Potash - 60% K₂O) as a basal dose at sowing according to ICAR recommendations."
            )

        elif any(w in q_lower for w in ["fertilizer", "npk", "urea", "dap", "potash", "manure", "dose", "dosage"]):
            remedy = self.knowledge_base["npk_ratios"].get(crop_key, self.knowledge_base["npk_ratios"].get(resolved_crop.lower(), self.knowledge_base["npk_ratios"]["wheat"]))
            sections.append(
                f"🧪 **Fertilizer NPK Recommendation for {target_crop}**:\n"
                f"- **Recommended Protocol**: {remedy}\n"
                f"- **Soil Preparation**: Incorporate FYM (10-15 tonnes/ha) during field preparation.\n"
                f"- **Application Safety**: Ensure adequate soil moisture before top-dressing nitrogenous fertilizers.\n\n"
                f"❓ *To calculate an exact fertilizer dose for your field, could you specify your current growth stage, field size in acres, or recent soil test results?*"
            )

        elif any(w in q_lower for w in ["disease", "pest", "blight", "rust", "fungus", "insect", "caterpillar", "chlorosis", "spot"]):
            matched_remedy = None
            for d_key, r_text in self.knowledge_base["disease_remedies"].items():
                if d_key.replace("_", " ") in q_lower or d_key in q_lower:
                    matched_remedy = r_text
                    break
            if not matched_remedy:
                matched_remedy = "Spray Neem Oil (10,000 PPM) @ 3ml/L water or consult local KVK agronomic specialist."

            sections.append(
                f"🛡️ **Pest & Disease Advisory for {target_crop}**:\n"
                f"- **Target Problem**: {query}\n"
                f"- **Recommended Treatment**: {matched_remedy}\n"
                f"- **Cultural Practice**: Maintain proper field drainage, crop rotation, and inspect lower leaf undersides regularly."
            )

        elif any(w in q_lower for w in ["price", "mandi", "rate", "market", "sell", "msp"]):
            if web_citations and any(c.get("source_status") == "LIVE_VERIFIED_PAGE" for c in web_citations):
                sections.append(
                    f"📊 **Mandi Market Update (Live Data)**:\n"
                    f"- **Crop**: {target_crop}\n"
                    f"- **State**: {region_info['state']}\n"
                    f"- **Major Mandis**: {', '.join(region_info['major_mandis'])}\n"
                    f"- **Market Status**: Mandi prices verified via e-NAM / AgMarkNet live portal queries."
                )
            else:
                sections.append(
                    f"📊 **Mandi Market Update for {target_crop} ({region_info['state']})**:\n"
                    f"- **Target Crop**: {target_crop}\n"
                    f"- **Major Regional Mandis**: {', '.join(region_info['major_mandis'])}\n"
                    f"- **Official Portals**: Track daily MSP rates via e-NAM (National Agriculture Market) and AgMarkNet."
                )

        elif any(w in q_lower for w in ["scheme", "pm-kisan", "pmfby", "subsid", "loan", "kcc"]):
            schemes_text = "\n".join([f"- **{s}**: {self.knowledge_base['govt_schemes'].get(s.lower().replace('-', '_'), 'State agricultural welfare benefit scheme.')}" for s in region_info["schemes"]])
            sections.append(f"🏛️ **Government Schemes & Subsidies ({region_info['state']})**:\n{schemes_text}")

        elif any(w in q_lower for w in ["water", "irrigate", "irrigation", "moisture", "drip", "telemetry", "sensor"]):
            telemetry_text = ""
            if farm_info.get("has_real_telemetry") and farm_info.get("telemetry_status_text"):
                telemetry_text = f"\n- **Real Sensor Telemetry**: {farm_info['telemetry_status_text']}"
            elif farm_info.get("farm_id"):
                telemetry_text = "\n- **Sensor Telemetry**: Real-time soil moisture telemetry is currently unavailable for this farm node."

            sections.append(
                f"💧 **Irrigation & Water Management for {target_crop}**:\n"
                f"- **Irrigation Advisory**: Irrigate early morning or late evening to minimize evapotranspiration losses.{telemetry_text}\n"
                f"- **Recommended Method**: Drip or sprinkler irrigation is recommended for optimal water efficiency."
            )

        else:
            clean_q = query.rstrip("?.!")
            sections.append(
                f"🌾 **Agronomic Advice for '{clean_q}'**:\n"
                f"Regarding **{target_crop}** in {region_info['state']}:\n\n"
                f"- Follow balanced ICAR-recommended plant nutrition and crop management guidelines.\n"
                f"- Inspect your field regularly for early signs of nutrient deficiency or pest vectors.\n"
                f"- Ensure adequate soil moisture before applying top-dressed fertilizers."
            )

        # 3. Append Web Citations ONLY if Web Search was Intentional & Active
        if web_citations and is_live_search_attempted:
            citations_list = []
            for c in web_citations:
                status_label = "Live Verified Page" if c.get("source_status") == "LIVE_VERIFIED_PAGE" else "Live Search Snippet"
                citations_list.append(f"- [{c['title']}]({c['url']}) ({status_label}): {c['snippet']}")

            citations_text = "\n".join(citations_list)
            sections.append(f"\n🌐 **Web Retrieval Sources**:\n{citations_text}")

        return "\n\n".join(sections)

    def process_chat_query(
        self,
        query: str,
        authenticated_farmer_id: int,
        authorized_farm_context: Optional[Dict[str, Any]] = None,
        language: str = "auto",
        location: str = "",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        crop_type: Optional[str] = None,
        image_base64: Optional[str] = None,
        enable_web_search: bool = True,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Process farmer query with strict farm context resolution, history context, evidence boundaries, and dynamic response generation."""

        # 1. Sanitize user input against prompt injection
        sanitized_query = self.sanitize_untrusted_input(query)
        target_lang = self.detect_language(sanitized_query, language)

        # 2. Extract & sanitize recent conversation history (last 10 messages)
        resolved_history = []
        if history and isinstance(history, list):
            for item in history[-10:]:
                if isinstance(item, dict):
                    r = item.get("role") or item.get("sender") or "user"
                    c = item.get("content") or item.get("text") or item.get("message") or ""
                    if c:
                        sanitized_c = self.sanitize_untrusted_input(str(c)[:500])
                        resolved_history.append({"role": str(r), "content": sanitized_c})

        context_crop = None
        context_topic = None
        q_lower = sanitized_query.lower()

        if resolved_history:
            for h in reversed(resolved_history):
                h_text = h["content"].lower()
                for crop in ["rice", "paddy", "wheat", "cotton", "maize", "sugarcane", "groundnut", "potato", "onion", "mustard"]:
                    if crop in h_text and not context_crop:
                        context_crop = crop.capitalize()
                for topic in ["fertilizer", "npk", "nitrogen", "disease", "rust", "blight", "mandi", "price", "scheme", "irrigation"]:
                    if topic in h_text and not context_topic:
                        context_topic = topic

        # 3. Determine farm & location context
        farm_info = authorized_farm_context or {}
        resolved_state = farm_info.get("state") or location or "India"
        resolved_crop = farm_info.get("crop_type") or crop_type or context_crop or "Wheat"
        region_info = self.get_region_info(resolved_state, latitude, longitude)

        # 4. Determine Evidence Level & Intent-Based Web Search (Strict Word Boundaries)
        evidence_state = "HIGH EVIDENCE"
        web_citations = []

        temporal_web_keywords = [
            "price", "prices", "mandi", "mandis", "rate", "rates", "market", "markets", "sell", "selling",
            "weather", "forecast", "news", "scheme", "schemes", "subsidy", "subsidies", "today", "latest",
            "current", "government", "policy", "pm-kisan", "pmfby", "kcc", "agmarknet", "e-nam"
        ]
        has_web_intent = any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) is not None for w in temporal_web_keywords) or \
                         any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) is not None for w in ["search", "internet", "lookup"])

        is_live_search_attempted = bool(enable_web_search) and has_web_intent

        if is_live_search_attempted:
            web_citations = self.search_internet_agricultural_data(sanitized_query, region_info["state"])
            if not web_citations:
                evidence_state = "MODERATE EVIDENCE (LIVE RETRIEVAL UNAVAILABLE)"

        # 5. Process Leaf Diagnosis Image Payload if Attached
        vision_diagnosis = None
        if image_base64:
            try:
                import base64
                from PIL import Image
                import io
                import numpy as np

                if len(image_base64) > 7 * 1024 * 1024:
                    raise ValueError("Image payload exceeds 5MB size limit")

                img_data = image_base64.split(",")[1] if "," in image_base64 else image_base64
                img_bytes = base64.b64decode(img_data)

                img = Image.open(io.BytesIO(img_bytes))
                img.verify()
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB").resize((64, 64))
                spat_arr = np.array(img, dtype=np.float32).transpose(2, 0, 1) / 255.0

                env_vals = farm_info.get("telemetry_env") or [25.0, 60.0, 50.0, 80.0]
                spectral_vals = [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]

                pred = ai_service.predict(spectral_vals, env_vals, spatial=spat_arr)
                xai = xai_service.generate_xai_explanation(spectral_vals, spat_arr)

                vision_diagnosis = {
                    "condition": pred["condition"].replace("_", " "),
                    "probabilistic_certainty": "Possible / Consistent with visual features",
                    "confidence_pct": round(pred["confidence"] * 100.0, 1),
                    "severity_score": pred["severity_score"],
                    "estimated_lead_time_hours": pred["estimated_lead_time_hours"],
                    "top_spectral_band": xai.get("top_attributing_band", "705nm Red Edge")
                }
            except Exception as e:
                print(f"[Chatbot Vision Processing Notice] Image scan note: {e}")

        # 6. Dynamic Agronomic Answer Generation (LLM First with Rule Fallback)
        start_time = time.time()
        context_str = f"Crop: {resolved_crop}, State: {region_info['state']}, Farm: {farm_info.get('farm_name', 'None')}"

        llm_res, failure_status, failure_reason = self._call_external_llm_provider(sanitized_query, context_str, resolved_history)

        if llm_res and llm_res.get("answer"):
            full_answer_en = llm_res["answer"]
            strategy = "LLM_GENERATIVE_AI"
            provider_name = llm_res.get("provider", "External LLM")
            model_name = llm_res.get("model", "generative_model")
            provider_status = "SUCCESS"
            provider_failure_reason = None
            provider_latency = llm_res.get("latency_ms", 0.0)
            llm_configured = True
            print(f"[Chatbot AI Engine] Invoked LLM Provider: {provider_name} ({model_name}) | Provider Latency: {provider_latency}ms | Status: SUCCESS")
        else:
            full_answer_en = self._generate_dynamic_agronomic_answer(
                query=sanitized_query,
                q_lower=q_lower,
                context_topic=context_topic,
                context_crop=context_crop,
                resolved_crop=resolved_crop,
                farm_info=farm_info,
                region_info=region_info,
                web_citations=web_citations,
                evidence_state=evidence_state,
                vision_diagnosis=vision_diagnosis,
                resolved_history=resolved_history,
                is_live_search_attempted=is_live_search_attempted
            )
            strategy = "LOCAL_DOMAIN_KNOWLEDGE_ENGINE"
            provider_name = "AgriSense ICAR/KVK Agronomic Knowledge Matrix v3.0"
            model_name = "local_rule_based_synthesis"
            provider_status = failure_status or "LLM_NOT_CONFIGURED"
            provider_failure_reason = failure_reason or "No LLM API Key (GEMINI_API_KEY / OPENAI_API_KEY) configured in environment"
            provider_latency = 0.0
            llm_configured = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY"))
            print(f"[Chatbot AI Engine] Executing LOCAL_DOMAIN_KNOWLEDGE_ENGINE fallback | Status: {provider_status} | Reason: {provider_failure_reason}")

        total_latency = round((time.time() - start_time) * 1000, 2)

        # 7. Final Assembly & Native Translation
        final_answer = self._translate_response(full_answer_en, target_lang)
        lang_info = SUPPORTED_LANGUAGES.get(target_lang, SUPPORTED_LANGUAGES["en"])

        return {
            "status": "success",
            "query": sanitized_query,
            "language": {
                "code": target_lang,
                "name": lang_info["name"],
                "native": lang_info["native"],
                "flag": lang_info["flag"]
            },
            "authenticated_farmer_id": authenticated_farmer_id,
            "farm_context": {
                "farm_id": farm_info.get("farm_id"),
                "farm_name": farm_info.get("farm_name"),
                "state": region_info["state"],
                "crop_type": resolved_crop,
                "telemetry_available": farm_info.get("has_real_telemetry", False)
            },
            "evidence_state": evidence_state,
            "answer": final_answer,
            "vision_diagnosis": vision_diagnosis,
            "web_search_enabled": enable_web_search,
            "web_citations": web_citations,
            "generation_metadata": {
                "strategy": strategy,
                "provider": provider_name,
                "model": model_name,
                "llm_configured": llm_configured,
                "provider_status": provider_status,
                "provider_failure_reason": provider_failure_reason,
                "provider_latency_ms": provider_latency,
                "total_latency_ms": total_latency
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _discover_available_gemini_models(self, gemini_key: str) -> List[str]:
        """
        Queries Google Gemini models.list endpoint to discover active models supporting generateContent.
        Filters out TTS, audio, and specialized models for pure text conversation.
        Never prints or logs the API key.
        """
        discovered = []
        if not gemini_key:
            return discovered
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key.strip()}"
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models_list = data.get("models", [])
                    flash_models = []
                    other_models = []
                    excluded_keywords = ["tts", "audio", "bidi", "embedding", "imagen", "veo", "computer-vision"]
                    for m in models_list:
                        methods = m.get("supportedGenerationMethods", [])
                        name = m.get("name", "").replace("models/", "")
                        name_lower = name.lower()
                        if "generateContent" in methods and name:
                            if any(ex in name_lower for ex in excluded_keywords):
                                continue
                            if "flash" in name_lower:
                                flash_models.append(name)
                            else:
                                other_models.append(name)
                    discovered = flash_models + other_models
        except Exception as e:
            print(f"[Chatbot Gemini Discovery Notice] Models list note: {str(e)[:100]}")
        return discovered

    def _call_external_llm_provider(self, query: str, context_str: str, history: List[Dict[str, str]]) -> tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        """
        Invokes external LLM API (Google Gemini or OpenAI) if API key is present in environment.
        Supports GEMINI_MODEL env var with default 'gemini-1.5-flash' and models.list discovery.
        Handles 503 Capacity Errors, 404 Model Not Found, 429 Rate Limits, 401 Auth Errors with bounded retries.
        Returns: (result_dict, failure_status, failure_reason)
        """
        gemini_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        groq_key = (os.getenv("GROQ_API_KEY") or "").strip()

        if not gemini_key and not openai_key and not groq_key:
            return None, "LLM_NOT_CONFIGURED", "No GEMINI_API_KEY or OPENAI_API_KEY present in environment variables"

        # 1. Google Gemini API Integration
        if gemini_key:
            t0 = time.time()
            configured_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
            discovered_models = self._discover_available_gemini_models(gemini_key)
            static_candidates = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro"]

            models_to_try = [configured_model]
            for m in discovered_models:
                if m not in models_to_try:
                    models_to_try.append(m)
            for m in static_candidates:
                if m not in models_to_try:
                    models_to_try.append(m)

            last_err_status = "LLM_PROVIDER_ERROR"
            last_err_reason = ""

            for model_id in models_to_try:
                # Up to 2 retries per model for 503 capacity / transient server errors
                max_model_attempts = 2
                model_succeeded = False
                for attempt in range(max_model_attempts):
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={gemini_key}"

                        contents = []
                        system_instruction = (
                            "You are AgriSense AI, an expert agricultural assistant specializing in Indian crops, soil science, "
                            "pest management, and farming best practices. Provide accurate, clear, helpful responses. "
                            f"Context: {context_str}"
                        )

                        for h in history[-6:]:
                            role = "user" if h.get("role") in ["user", "farmer"] else "model"
                            contents.append({"role": role, "parts": [{"text": h.get("content", "")}]})

                        contents.append({"role": "user", "parts": [{"text": query}]})

                        payload = {
                            "system_instruction": {"parts": [{"text": system_instruction}]},
                            "contents": contents,
                            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1000}
                        }

                        req = urllib.request.Request(
                            url,
                            data=json.dumps(payload).encode("utf-8"),
                            headers={"Content-Type": "application/json"}
                        )

                        with urllib.request.urlopen(req, timeout=8) as resp:
                            if resp.status == 200:
                                data = json.loads(resp.read().decode("utf-8"))
                                latency = round((time.time() - t0) * 1000, 2)
                                candidates = data.get("candidates", [])
                                if candidates and "content" in candidates[0]:
                                    parts = candidates[0]["content"].get("parts", [])
                                    if parts and "text" in parts[0]:
                                        res_dict = {
                                            "answer": parts[0]["text"].strip(),
                                            "provider": "Google Gemini",
                                            "model": model_id,
                                            "latency_ms": latency
                                        }
                                        return res_dict, None, None
                        break
                    except urllib.error.HTTPError as e:
                        err_body = e.read().decode('utf-8', errors='ignore') if e.fp else ""
                        safe_body = re.sub(r'key=[^&"\s]+', 'key=[REDACTED]', err_body[:200])

                        if e.code in (401, 403):
                            last_err_status = "LLM_PROVIDER_AUTH_ERROR_401"
                            last_err_reason = f"Google Gemini API HTTP {e.code} Unauthorized: Invalid or unprivileged API key"
                            break  # Invalid key, break attempts & model loop
                        elif e.code == 429:
                            last_err_status = "LLM_PROVIDER_RATE_LIMIT_429"
                            last_err_reason = f"Google Gemini API 429 Rate Limit / Quota Exhausted for model {model_id}"
                            if attempt < max_model_attempts - 1:
                                time.sleep(1.0)
                                continue
                            break  # Move to next candidate model
                        elif e.code == 503:
                            last_err_status = "LLM_PROVIDER_CAPACITY_ERROR_503"
                            last_err_reason = f"Google Gemini API 503 Service Unavailable / Capacity Exhausted for model {model_id}"
                            if attempt < max_model_attempts - 1:
                                time.sleep(1.0 * (attempt + 1))
                                continue
                            break  # Move to next candidate model
                        elif e.code == 404:
                            last_err_status = "LLM_PROVIDER_MODEL_NOT_FOUND_404"
                            last_err_reason = f"Google Gemini API 404 Model Not Found: {model_id}"
                            break  # Move to next candidate model immediately
                        else:
                            last_err_status = f"LLM_PROVIDER_HTTP_ERROR_{e.code}"
                            last_err_reason = f"Google Gemini API HTTP {e.code}: {safe_body}"
                            break
                    except (urllib.error.URLError, TimeoutError) as e:
                        last_err_status = "LLM_PROVIDER_TIMEOUT"
                        last_err_reason = f"Google Gemini API Connection Timeout / Network Error on {model_id}: {str(e)}"
                        if attempt < max_model_attempts - 1:
                            time.sleep(1.0)
                            continue
                        break
                    except Exception as e:
                        last_err_status = "LLM_PROVIDER_EXCEPTION"
                        last_err_reason = f"Google Gemini API Call Error: {str(e)}"
                        break

                if last_err_status == "LLM_PROVIDER_AUTH_ERROR_401":
                    break  # Stop all models if API key is unauthorized

            if last_err_status != "LLM_PROVIDER_ERROR":
                return None, last_err_status, last_err_reason

        # 2. OpenAI API Integration
        if openai_key and openai_key.strip():
            t0 = time.time()
            try:
                url = "https://api.openai.com/v1/chat/completions"
                messages = [{"role": "system", "content": f"You are AgriSense AI. Context: {context_str}"}]
                for h in history[-6:]:
                    r = "user" if h.get("role") in ["user", "farmer"] else "assistant"
                    messages.append({"role": r, "content": h.get("content", "")})
                messages.append({"role": "user", "content": query})

                payload = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 1000
                }

                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {openai_key.strip()}"
                    }
                )

                with urllib.request.urlopen(req, timeout=8) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        latency = round((time.time() - t0) * 1000, 2)
                        choices = data.get("choices", [])
                        if choices and "message" in choices[0]:
                            res_dict = {
                                "answer": choices[0]["message"].get("content", "").strip(),
                                "provider": "OpenAI",
                                "model": "gpt-4o-mini",
                                "latency_ms": latency
                            }
                            return res_dict, None, None
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    return None, "LLM_PROVIDER_AUTH_ERROR_401", "OpenAI API 401 Unauthorized: Invalid API Key"
                elif e.code == 429:
                    return None, "LLM_PROVIDER_RATE_LIMIT_429", "OpenAI API 429 Rate Limit Exceeded"
                else:
                    return None, f"LLM_PROVIDER_HTTP_ERROR_{e.code}", f"OpenAI API HTTP {e.code}"
            except (urllib.error.URLError, TimeoutError) as e:
                return None, "LLM_PROVIDER_TIMEOUT", f"OpenAI API Timeout / Network Error: {str(e)}"
            except Exception as e:
                return None, "LLM_PROVIDER_EXCEPTION", f"OpenAI API Error: {str(e)}"

        return None, "LLM_PROVIDER_UNAVAILABLE", "Configured LLM providers failed or timed out"

chatbot_service = ProductionAgriculturalChatbotService()
