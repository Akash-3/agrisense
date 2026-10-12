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

    @staticmethod
    def count_words(text: str) -> int:
        """Counts whitespace-delimited words in text."""
        if not text:
            return 0
        return len(text.split())

    def enforce_word_limit(self, text: str, max_words: int = 100) -> str:
        """
        Enforces a strict maximum word limit (default 100 words, aiming for 40-80 words).
        Preserves direct Answer, actionable steps, and essential Caution/Safety warnings.
        Avoids blind truncation at the 100th word by using structural and sentence-level compression.
        """
        if not text or self.count_words(text) <= max_words:
            return text

        # 1. Strip conversational fluff/filler
        fluff_patterns = [
            r'^(?:Hello|Namaste|Greetings|Hi)\s*(?:from\s+AgriSense\s*AI!?)?[,\.\s]*',
            r'(?:As an AI agricultural assistant|I am here to help you with|In summary|In conclusion)[,\.\s]*',
            r'(?:Please let me know if you need any further assistance|Feel free to ask more questions)[,\.\s]*'
        ]
        cleaned = text.strip()
        for pat in fluff_patterns:
            cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE).strip()

        if self.count_words(cleaned) <= max_words:
            return cleaned

        # 2. Check for distinct Caution/Warning/Safety lines
        caution_lines = []
        other_lines = []
        lines = [line.strip() for line in cleaned.split('\n') if line.strip()]
        for line in lines:
            line_lower = line.lower()
            if any(k in line_lower for k in ['**caution', 'caution:', '⚠️', '**warning', 'warning:', 'safety precaution', 'do not apply', 'avoid excess', 'avoid waterlogging']):
                caution_lines.append(line)
            else:
                other_lines.append(line)

        caution_block = '\n'.join(caution_lines)
        caution_words = self.count_words(caution_block)
        allowed_other_words = max_words - caution_words if caution_words < max_words else max_words

        # 3. Line & section budget building
        selected_lines = []
        current_words = 0
        for line in other_lines:
            line_w = self.count_words(line)
            if current_words + line_w <= allowed_other_words:
                selected_lines.append(line)
                current_words += line_w
            else:
                sentences = re.split(r'(?<=[.!?])\s+', line)
                for s in sentences:
                    s_w = self.count_words(s)
                    if current_words + s_w <= allowed_other_words:
                        selected_lines.append(s)
                        current_words += s_w
                    else:
                        break
                break

        if selected_lines:
            candidate = '\n'.join(selected_lines)
            if caution_block and caution_block not in candidate:
                candidate = candidate + '\n' + caution_block
            if self.count_words(candidate) <= max_words:
                return candidate.strip()

        # 4. Sentence-level compression across full text
        sentences = re.split(r'(?<=[.!?])\s+', cleaned)
        selected_sentences = []
        current_count = 0
        caution_sentences = [
            s for s in sentences
            if any(k in s.lower() for k in ['caution', 'warning', '⚠️', 'danger', 'avoid', 'do not', 'safety'])
        ]
        key_caution = caution_sentences[0] if caution_sentences else ''
        key_caution_words = self.count_words(key_caution)
        target_budget = max_words - key_caution_words if key_caution_words < 30 else max_words

        for s in sentences:
            if s == key_caution:
                continue
            s_w = self.count_words(s)
            if current_count + s_w <= target_budget:
                selected_sentences.append(s)
                current_count += s_w
            else:
                break

        if key_caution and key_caution not in selected_sentences:
            selected_sentences.append(key_caution)

        result = ' '.join(selected_sentences).strip()
        if result and self.count_words(result) <= max_words:
            return result

        # 5. Safe clause boundary fallback if single sentence exceeds limit
        tokens = cleaned.split()
        if len(tokens) > max_words:
            truncated_tokens = tokens[:max_words]
            joined = ' '.join(truncated_tokens)
            last_punc = max(joined.rfind('.'), joined.rfind('!'), joined.rfind('?'), joined.rfind(';'))
            if last_punc > len(joined) // 2:
                joined = joined[:last_punc + 1]
            elif not joined.endswith('.'):
                joined += '.'
            return joined

        return cleaned

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
        """Generates concise, query-tailored agronomic responses strictly under 100 words (aiming for 40-80 words)."""
        sections = []

        # 1. Vision Diagnosis Payload (if leaf image was attached)
        if vision_diagnosis:
            remedy = self.knowledge_base["disease_remedies"].get("leaf_blight")
            sections.append(
                f"🔬 **Visual Scan ({vision_diagnosis['condition']}):**\n"
                f"- **Confidence**: {vision_diagnosis['confidence_pct']}% | Severity: {vision_diagnosis['severity_score']}/100\n"
                f"- **Treatment**: {remedy}"
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

        # 2. Query Intent Analysis & Direct Knowledge Synthesis (Concise Answer, Action, Caution)
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
                "🌱 **Soil & Plants (Simple Explanation):**\n"
                "**Answer:** Soil is a natural kitchen for plants, providing air, water, and food.\n"
                "**Action:** Roots take up Nitrogen, Phosphorus, and Potassium to grow strong stems and green leaves.\n"
                "**Caution:** Keep soil moist and fertile with organic compost so plants thrive."
            )

        elif is_one_sentence:
            if "water" in q_lower:
                sections.append(
                    "**Answer:** Plants need water to transport nutrients from roots to leaves and perform photosynthesis for energy and survival."
                )
            else:
                sections.append(
                    "**Answer:** Plants require balanced soil nutrients and water to synthesize chlorophyll, build cellular structures, and achieve healthy growth."
                )

        elif is_nitrogen_vs_iron:
            sections.append(
                "🍃 **Nitrogen vs. Iron Deficiency Comparison:**\n"
                "**Answer:** Both cause leaf yellowing, but differ in plant mobility and location.\n"
                "- **1. Location:** Nitrogen is mobile; deficiency yellowing starts on older lower leaves. Iron is immobile; yellowing appears on youngest top leaves.\n"
                "- **2. Pattern:** Nitrogen produces uniform chlorosis across the leaf blade. Iron causes distinct interveinal chlorosis (yellow tissue, dark green veins).\n"
                "- **3. Action:** Apply Urea or Nano Urea for Nitrogen; foliar spray 0.5% Ferrous Sulphate ($FeSO_4$) for Iron."
            )

        elif is_photosynthesis_query:
            sections.append(
                "🌿 **Photosynthesis in Plants:**\n"
                "**Answer:** Photosynthesis is the biological process where green leaves convert sunlight, water ($H_2O$), and carbon dioxide ($CO_2$) into glucose energy and oxygen ($O_2$).\n"
                "**Action:** Maintain adequate sunlight and balanced Nitrogen and Magnesium nutrition to support active chlorophyll molecules."
            )

        is_potassium_query = any(w in q_lower for w in ["potassium", "potash"]) or re.search(r'\b(k)\b', q_lower) is not None
        is_npk_vs_single = "difference between npk" in q_lower or ("npk" in q_lower and "single" in q_lower) or ("complex" in q_lower and "straight" in q_lower)
        is_organic_matter = any(w in q_lower for w in ["organic matter", "humus", "compost", "fym"])
        is_soil_ph = "ph" in q_lower and ("soil" in q_lower or "acid" in q_lower or "alkaline" in q_lower or "absorption" in q_lower)
        is_safety = any(w in q_lower for w in ["safety", "precaution", "precautions", "handling", "protective", "ppe"])

        if is_npk_vs_single:
            sections.append(
                "🧪 **NPK Complex vs. Single-Nutrient Fertilizers:**\n"
                "**Answer:** NPK complex fertilizers supply multiple primary nutrients (N, P, K) in a balanced ratio for basal application. Single-nutrient fertilizers (Urea for N, SSP for P, MOP for K) deliver one specific element.\n"
                "**Action:** Use NPK for balanced base fertilization and single fertilizers for targeted deficiency correction."
            )

        elif is_organic_matter:
            sections.append(
                "🪱 **Soil Organic Matter (SOM) & Soil Health:**\n"
                "**Answer:** Soil Organic Matter improves soil structure, water retention, and microbial activity.\n"
                "- **Action 1:** Apply 10–15 tonnes/ha FYM or compost during land preparation.\n"
                "- **Action 2:** Retain crop residues and plant green manure crops.\n"
                "- **Benefit:** Prevents nutrient leaching and boosts crop drought resilience."
            )

        elif is_soil_ph:
            sections.append(
                "🧪 **Soil pH & Nutrient Absorption:**\n"
                "**Answer:** Soil pH governs nutrient availability to plant roots. The optimal range for most field crops is 6.0–7.5.\n"
                "- **Action:** Apply agricultural lime to raise acidic pH (<6.0), or gypsum to lower alkaline pH (>7.5).\n"
                "- **Caution:** Extreme soil pH locks up essential Phosphorus, Iron, and Zinc."
            )

        elif is_safety:
            sections.append(
                "⚠️ **Safety Precautions for Fertilizer Handling:**\n"
                "**Answer:** Follow these safety practices when storing and applying fertilizers:\n"
                "- **Action 1:** Wear protective rubber gloves, safety goggles, and a dust mask when handling Urea or DAP.\n"
                "- **Action 2:** Store bags off the ground in a dry, ventilated, locked shed away from children.\n"
                "- **Caution:** Wash hands and face thoroughly with soap and clean water immediately after application."
            )

        elif is_nitrogen_query or ("npk" in q_lower and "ratio" not in q_lower and "dose" not in q_lower):
            if is_confirm_query:
                sections.append(
                    f"🧪 **Confirming Nitrogen Deficiency in {target_crop}:**\n"
                    f"**Answer:** V-shaped lower leaf yellowing indicates nitrogen deficiency, but laboratory confirmation is recommended.\n"
                    f"- **Action 1:** Perform a Soil Health Card laboratory test to measure available Nitrogen ($N$).\n"
                    f"- **Action 2:** Test leaf chlorophyll levels using a SPAD chlorophyll meter.\n"
                    f"- **Caution:** Rule out waterlogging and Sulfur deficiency, which cause similar yellowing."
                )
            elif is_remedy_query or ("do" in q_lower and "deficiency" in q_lower) or ("next" in q_lower and "do" in q_lower):
                sections.append(
                    f"💊 **Remedial Actions for Nitrogen Deficiency in {target_crop}:**\n"
                    f"**Answer:** Address nitrogen deficiency promptly to prevent tillering loss and stunted growth.\n"
                    f"- **Action 1:** Top-dress Urea (46% N) @ 25–30 kg per acre (~60 kg/ha) with adequate soil moisture.\n"
                    f"- **Action 2:** Spray 2% Urea solution (20g/L water) or Nano Urea @ 2–4 mL/L for rapid foliar absorption.\n"
                    f"- **Caution:** Never apply dry urea on parched soil to avoid root burn."
                )
            elif is_deficiency_query or "identify" in q_lower or "symptom" in q_lower or "look for" in q_lower:
                sections.append(
                    f"🔍 **Identifying Nitrogen Deficiency in {target_crop}:**\n"
                    f"**Answer:** Nitrogen deficiency symptoms appear distinctly on foliage:\n"
                    f"- **Symptoms:** Older lower leaves turn yellow first in a V-shape from leaf tip down the midrib, with stunted tillering.\n"
                    f"- **Action:** Top-dress Urea or spray foliar Nano Urea with irrigation.\n"
                    f"- **Caution:** Confirm via soil test, as waterlogged roots cause similar yellowing."
                )
            elif is_importance_query or "important" in q_lower or "why" in q_lower:
                sections.append(
                    f"🌾 **Importance of Nitrogen for {target_crop}:**\n"
                    f"**Answer:** Nitrogen is an essential macronutrient that drives chlorophyll production, vegetative vigor, and tillering in {target_crop}.\n"
                    f"- **Action 1:** Provides protein building blocks for cell division and grain filling.\n"
                    f"- **Action 2:** Follow balanced ICAR-recommended NPK ratios (e.g. 120:60:40 kg/ha for Wheat).\n"
                    f"- **Caution:** Avoid excess nitrogen, which induces lodging and pest susceptibility."
                )
            else:
                crop_note = f" In {target_crop}, maintain adequate nitrogen during early tillering." if target_crop else ""
                sections.append(
                    f"🌱 **What is Nitrogen in Plants?**\n"
                    f"**Answer:** Nitrogen (N) is a primary macronutrient essential for chlorophyll synthesis, protein formation, and vigorous vegetative growth.{crop_note}\n"
                    f"- **Action:** Apply recommended nitrogen in split doses: half basal at sowing and half top-dressed.\n"
                    f"- **Caution:** Avoid over-fertilization to prevent vegetative lodging and aphid infestations."
                )

        elif is_potassium_query:
            sections.append(
                f"🧪 **Potassium (K) in {target_crop}:**\n"
                f"**Answer:** Potassium regulates stomatal water balance, activates enzymes, and improves disease and lodging resistance in {target_crop}.\n"
                f"- **Action:** Apply MOP (Muriate of Potash - 60% K₂O) @ 20–30 kg/acre as a basal application at sowing.\n"
                f"- **Caution:** Potassium deficiency leads to weak stems, lodging, and reduced grain test weight."
            )

        elif any(w in q_lower for w in ["fertilizer", "npk", "urea", "dap", "potash", "manure", "dose", "dosage"]):
            remedy = self.knowledge_base["npk_ratios"].get(crop_key, self.knowledge_base["npk_ratios"].get(resolved_crop.lower(), self.knowledge_base["npk_ratios"]["wheat"]))
            sections.append(
                f"🧪 **Fertilizer NPK Recommendation for {target_crop}:**\n"
                f"**Answer:** Recommended ICAR fertilizer dose: {remedy}.\n"
                f"- **Action 1:** Apply full P and K and 50% N as a basal application at sowing.\n"
                f"- **Action 2:** Top-dress remaining 50% N at first irrigation/tillering.\n"
                f"- **Caution:** Ensure adequate soil moisture before top-dressing nitrogen fertilizers."
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
                f"🛡️ **Pest & Disease Advisory for {target_crop}:**\n"
                f"**Answer:** For {query} in {target_crop}, prompt preventive management is recommended.\n"
                f"- **Action:** {matched_remedy}\n"
                f"- **Practice:** Maintain proper field drainage and inspect lower leaf undersides regularly.\n"
                f"- **Caution:** Follow recommended chemical dilution rates; avoid spraying in strong wind."
            )

        elif any(w in q_lower for w in ["price", "mandi", "rate", "market", "sell", "msp"]):
            mandi_list = ', '.join(region_info['major_mandis'][:2])
            sections.append(
                f"📊 **Mandi Market Rates for {target_crop} ({region_info['state']}):**\n"
                f"**Answer:** Track daily market arrivals and MSP modal rates on official agricultural portals.\n"
                f"- **Action:** Visit e-NAM (enam.gov.in) or AgMarkNet (agmarknet.gov.in) for live prices.\n"
                f"- **Key Mandis:** {mandi_list}."
            )

        elif any(w in q_lower for w in ["scheme", "pm-kisan", "pmfby", "subsid", "loan", "kcc"]):
            schemes_text = ", ".join([f"{s}" for s in region_info["schemes"][:3]])
            sections.append(
                f"🏛️ **Government Agricultural Schemes ({region_info['state']}):**\n"
                f"**Answer:** Key government welfare schemes available: {schemes_text}.\n"
                f"- **Action:** Apply at your local Common Service Center (CSC) or state agriculture office with your Aadhaar and land records.\n"
                f"- **Support:** Access PM-KISAN (Rs 6,000/yr) and PMFBY crop insurance."
            )

        elif any(w in q_lower for w in ["water", "irrigate", "irrigation", "moisture", "drip", "telemetry", "sensor"]):
            telemetry_text = ""
            if farm_info.get("has_real_telemetry") and farm_info.get("telemetry_status_text"):
                telemetry_text = f" Sensor data: {farm_info['telemetry_status_text']}."

            sections.append(
                f"💧 **Irrigation Advisory for {target_crop}:**\n"
                f"**Answer:** Irrigate during critical growth stages like crown root initiation and flowering.{telemetry_text}\n"
                f"- **Action:** Irrigate early morning or evening to minimize evaporation. Use drip or sprinkler methods for water savings.\n"
                f"- **Caution:** Avoid waterlogging in the root zone to prevent root rot."
            )

        else:
            clean_q = query.rstrip("?.!")
            sections.append(
                f"🌾 **Agronomic Advice for '{clean_q}':**\n"
                f"**Answer:** For {target_crop} in {region_info['state']}, follow balanced ICAR crop management practices.\n"
                f"- **Action 1:** Maintain balanced soil nutrients and test soil health every two years.\n"
                f"- **Action 2:** Inspect fields weekly for early symptoms of pests or nutrient deficiency.\n"
                f"- **Caution:** Always ensure soil moisture before applying top-dressed fertilizers."
            )

        # 3. Append Web Citations ONLY if Web Search was Intentional & Active (Compact)
        if web_citations and is_live_search_attempted:
            citations_list = []
            for c in web_citations[:2]:
                citations_list.append(f"- [{c['title']}]({c['url']})")
            citations_text = "\n".join(citations_list)
            sections.append(f"🌐 **Sources:**\n{citations_text}")

        raw_combined = "\n\n".join(sections)
        return self.enforce_word_limit(raw_combined, max_words=100)

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
            full_answer_en = self.enforce_word_limit(llm_res["answer"], max_words=100)
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
            full_answer_en = self.enforce_word_limit(full_answer_en, max_words=100)
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
        translated_answer = self._translate_response(full_answer_en, target_lang)
        final_answer = self.enforce_word_limit(translated_answer, max_words=100)
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
                            "You are AgriSense AI, an expert agricultural assistant for Indian farmers. "
                            "Every response must be strictly concise, under 100 words (aim for 40 to 80 words). "
                            "Answer the user's specific request directly and factually without fluff or greetings. "
                            "Where appropriate, structure response with short points or: Answer (direct response), Action (1-3 practical steps), Caution (essential safety/health warning, only if needed). "
                            "If uncertain or lacking crop data, state it immediately and advise consulting the nearest Krishi Vigyan Kendra (KVK) or agronomist.\n"
                            f"Farm Context: {context_str}"
                        )

                        for h in history[-6:]:
                            role = "user" if h.get("role") in ["user", "farmer"] else "model"
                            contents.append({"role": role, "parts": [{"text": h.get("content", "")}]})

                        contents.append({"role": "user", "parts": [{"text": query}]})

                        payload = {
                            "system_instruction": {"parts": [{"text": system_instruction}]},
                            "contents": contents,
                            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 350}
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
                openai_sys = (
                    "You are AgriSense AI, an expert agricultural assistant for Indian farmers. "
                    "Every response must be strictly concise, under 100 words (aim for 40 to 80 words). "
                    "Answer directly without greetings or fluff. Use short points or Answer/Action/Caution structure where appropriate. "
                    f"Farm Context: {context_str}"
                )
                messages = [{"role": "system", "content": openai_sys}]
                for h in history[-6:]:
                    r = "user" if h.get("role") in ["user", "farmer"] else "assistant"
                    messages.append({"role": r, "content": h.get("content", "")})
                messages.append({"role": "user", "content": query})

                payload = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 250
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
