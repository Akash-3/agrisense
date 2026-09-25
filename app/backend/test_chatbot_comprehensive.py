import sys
import os
import time
import pytest
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:8000,http://127.0.0.1:8000"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_123456789"
test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_comprehensive_tmp.db'))
os.environ["DB_PATH"] = test_db_path

from fastapi.testclient import TestClient
from database import init_db
init_db()

import main
from services.chatbot_service import chatbot_service, SUPPORTED_LANGUAGES

client = TestClient(main.app)

# 106+ COMPREHENSIVE PROMPTS ACROSS ALL 13 SUPPORTED LANGUAGES
PROMPT_CATALOG: List[Dict[str, Any]] = [
    # --- 1. ENGLISH PROMPTS (10) ---
    {"query": "What is the recommended NPK fertilizer ratio for wheat crop?", "lang": "en", "loc": "Punjab", "crop": "Wheat"},
    {"query": "How to prevent yellow rust outbreak in wheat in cool weather?", "lang": "en", "loc": "Haryana", "crop": "Wheat"},
    {"query": "What is the current Mandi price of paddy in Punjab?", "lang": "en", "loc": "Punjab", "crop": "Paddy"},
    {"query": "How to apply for PM-KISAN ₹6000 annual subsidy scheme?", "lang": "en", "loc": "Uttar Pradesh", "crop": "General"},
    {"query": "What are the benefits of Kisan Credit Card (KCC) for small farmers?", "lang": "en", "loc": "Bihar", "crop": "General"},
    {"query": "How to control caterpillar pest in cotton fields using organic neem oil?", "lang": "en", "loc": "Gujarat", "crop": "Cotton"},
    {"query": "What is the optimal irrigation schedule for sugarcane during summer?", "lang": "en", "loc": "Maharashtra", "crop": "Sugarcane"},
    {"query": "How to treat chlorosis and iron deficiency in groundnut crops?", "lang": "en", "loc": "Tamil Nadu", "crop": "Groundnut"},
    {"query": "What is the premium rate for PMFBY crop insurance for Rabi crops?", "lang": "en", "loc": "Rajasthan", "crop": "Mustard"},
    {"query": "How to measure soil pH and electrical conductivity using Soil Health Card?", "lang": "en", "loc": "Karnataka", "crop": "Maize"},

    # --- 2. HINDI PROMPTS (10) ---
    {"query": "गेहूं की फसल में एनपीके (NPK) उर्वरक की सही मात्रा क्या है?", "lang": "hi", "loc": "Punjab", "crop": "Wheat"},
    {"query": "धान की फसल में कीट नियंत्रण के लिए नीम तेल का प्रयोग कैसे करें?", "lang": "hi", "loc": "Uttar Pradesh", "crop": "Paddy"},
    {"query": "पंजाब की मंडियों में आज गेहूं का ताजा भाव क्या है?", "lang": "hi", "loc": "Punjab", "crop": "Wheat"},
    {"query": "पीएम किसान सम्मान निधि योजना में आवेदन करने की पात्रता क्या है?", "lang": "hi", "loc": "Bihar", "crop": "General"},
    {"query": "कपास की खेती में पत्ती धब्बा रोग का जैविक इलाज बताएं?", "lang": "hi", "loc": "Gujarat", "crop": "Cotton"},
    {"query": "मक्के की फसल में सिंचाई का सही समय और तरीका क्या है?", "lang": "hi", "loc": "Bihar", "crop": "Maize"},
    {"query": "सरसों की फसल को पाले से बचाने के उपाय क्या हैं?", "lang": "hi", "loc": "Haryana", "crop": "Mustard"},
    {"query": "मृदा स्वास्थ्य कार्ड से मिट्टी की जांच कैसे करवाएं?", "lang": "hi", "loc": "Madhya Pradesh", "crop": "Soybean"},
    {"query": "गन्ने की फसल में रेड रॉट बीमारी से बचाव की सलाह दें?", "lang": "hi", "loc": "Uttar Pradesh", "crop": "Sugarcane"},
    {"query": "किसान क्रेडिट कार्ड योजना से ₹3 लाख का ऋण कैसे प्राप्त करें?", "lang": "hi", "loc": "Rajasthan", "crop": "Bajra"},

    # --- 3. TAMIL PROMPTS (8) ---
    {"query": "நெல் பயிரில் உரம் இடும் சரியான NPK அளவு என்ன?", "lang": "ta", "loc": "Tamil Nadu", "crop": "Paddy"},
    {"query": "தமிழ்நாட்டில் இன்று நெல் மண்டி சந்தை விலை என்ன?", "lang": "ta", "loc": "Tamil Nadu", "crop": "Paddy"},
    {"query": "பிஎம் கிசான் ₹6000 உதவித்தொகை பெற விண்ணப்பிப்பது எப்படி?", "lang": "ta", "loc": "Tamil Nadu", "crop": "General"},
    {"query": "கரும்பு பயிரில் பூச்சி தாக்குதலை தடுக்கும் இயற்கை மருந்துகள் யாவை?", "lang": "ta", "loc": "Tamil Nadu", "crop": "Sugarcane"},
    {"query": "வேர்க்கடலை பயிரில் மஞ்சள் நோய் கட்டுப்படுத்துவது எப்படி?", "lang": "ta", "loc": "Tamil Nadu", "crop": "Groundnut"},
    {"query": "பயிர் காப்பீடு பிஎம்எஃப்பிஒய் திட்டம் பற்றிய தகவல்கள் தரவும்?", "lang": "ta", "loc": "Tamil Nadu", "crop": "Cotton"},
    {"query": "வாழை பயிருக்கு சொட்டுநீர் பாசனம் அமைப்பது எப்படி?", "lang": "ta", "loc": "Tamil Nadu", "crop": "Banana"},
    {"query": "தென்னை மரங்களில் சிவப்பு கூன் வண்டு கட்டுப்பாடு முறைகள் என்ன?", "lang": "ta", "loc": "Tamil Nadu", "crop": "Coconut"},

    # --- 4. TELUGU PROMPTS (8) ---
    {"query": "వరి సాగులో వాడవలసిన NPK ఎరువుల మోతాదు ఎంత?", "lang": "te", "loc": "Telangana", "crop": "Paddy"},
    {"query": "వరంగల్ మార్కెట్లో ఈరోజు మిర్చి మరియు పత్తి ధరలు ఎలా ఉన్నాయి?", "lang": "te", "loc": "Telangana", "crop": "Chilli"},
    {"query": "రైతు బంధు మరియు పిఎం కిసాన్ పథకాల నిధులు పొందడం ఎలా?", "lang": "te", "loc": "Telangana", "crop": "General"},
    {"query": "పత్తి పంటలో గులాబీ రంగు పురుగు నివారణకు ఎలాంటి మందులు వాడాలి?", "lang": "te", "loc": "Andhra Pradesh", "crop": "Cotton"},
    {"query": "మొక్కజొన్న పంటలో కత్తెర పురుగు నివారణ చర్యలు చెప్పండి?", "lang": "te", "loc": "Telangana", "crop": "Maize"},
    {"query": "వైఎస్ఆర్ రైతు భరోసా పథకం లబ్ధిదారుల అర్హతలు ఏమిటి?", "lang": "te", "loc": "Andhra Pradesh", "crop": "General"},
    {"query": "పసుపు పంట తొందరగా నాటుకోవడానికి అనుకూల సమయం ఏది?", "lang": "te", "loc": "Telangana", "crop": "Turmeric"},
    {"query": "మామిడి తోటలలో పూత నిలవడానికి పిచికారీ చేయవలసిన మందులు ఏవి?", "lang": "te", "loc": "Andhra Pradesh", "crop": "Mango"},

    # --- 5. KANNADA PROMPTS (8) ---
    {"query": "ಬರಿ ಬೆಳೆಗೆ ಎನ್‌ಪಿಕೆ ರಸಗೊಬ್ಬರ ಹಾಕುವ ಸರಿಯಾದ ಪ್ರಮಾಣ ಎಷ್ಟು?", "lang": "kn", "loc": "Karnataka", "crop": "Paddy"},
    {"query": "ಕರ್ನಾಟಕದ ಮಂಡಿಗಳಲ್ಲಿ ಇಂದಿನ ರಾಗಿ ಮತ್ತು ಮೆಕ್ಕೆಜೋಳದ ಧಾರಣೆ ಎಷ್ಟಿದೆ?", "lang": "kn", "loc": "Karnataka", "crop": "Ragi"},
    {"query": "ಪಿಎಂ ಕಿಸಾನ್ ಯೋಜನೆಯಡಿ ₹6000 ಹಣ ಪಡೆಯಲು ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು ಹೇಗೆ?", "lang": "kn", "loc": "Karnataka", "crop": "General"},
    {"query": "ಅಡಿಕೆ ಮರಗಳಲ್ಲಿ ಕಾಯಿ ಉದುರುವಿಕೆ ತಡೆಯಲು ಉಪಾಯಗಳೇನು?", "lang": "kn", "loc": "Karnataka", "crop": "Arecanut"},
    {"query": "ಕಬ್ಬಿನ ಬೆಳೆಗೆ ಹನಿ ನೀರಾವರಿ ಪದ್ಧತಿ ಅಳವಡಿಸುವುದು ಹೇಗೆ?", "lang": "kn", "loc": "Karnataka", "crop": "Sugarcane"},
    {"query": "ಕೃಷಿ ಭಾಗ್ಯ ಯೋಜನೆಯಡಿ ಶೇಕಡಾ 80 ರಷ್ಟು ಸಹಾಯಧನ ಪಡೆಯುವುದು ಹೇಗೆ?", "lang": "kn", "loc": "Karnataka", "crop": "General"},
    {"query": "ಹತ್ತಿ ಬೆಳೆಯಲ್ಲಿ ನುಸಿ ಮತ್ತು ಜಿಗಿಹುಳುಗಳ ನಿಯಂತ್ರಣ ಹೇಗೆ?", "lang": "kn", "loc": "Karnataka", "crop": "Cotton"},
    {"query": "ಕಾಫಿ ತೋಟದಲ್ಲಿ ಕಳೆ ನಿಯಂತ್ರಣ ಮತ್ತು ಗೊಬ್ಬರ ನಿರ್ವಹಣೆ ಹೇಗೆ?", "lang": "kn", "loc": "Karnataka", "crop": "Coffee"},

    # --- 6. MARATHI PROMPTS (8) ---
    {"query": "गहू पिकासाठी खतांचे एनपीके (NPK) योग्य प्रमाण काय आहे?", "lang": "mr", "loc": "Maharashtra", "crop": "Wheat"},
    {"query": "लासलगाव मंडीत आज कांद्याचा ताजा बाजार भाव काय चालू आहे?", "lang": "mr", "loc": "Maharashtra", "crop": "Onion"},
    {"query": "नमो शेतकरी महासन्मान निधी योजनेचा लाभ कसा घ्यावा?", "lang": "mr", "loc": "Maharashtra", "crop": "General"},
    {"query": "कापूस पिकावरील बोंड अळीचे नियंत्रण करण्यासाठी उपाय सांगा?", "lang": "mr", "loc": "Maharashtra", "crop": "Cotton"},
    {"query": "सोयाबीन पिकातील पिवळा मोझॅक रोगावर प्रतिबंधात्मक उपाय काय?", "lang": "mr", "loc": "Maharashtra", "crop": "Soybean"},
    {"query": "उसाची उत्पादकता वाढवण्यासाठी ठिबक सिंचन आणि खत व्यवस्थापन कसे करावे?", "lang": "mr", "loc": "Maharashtra", "crop": "Sugarcane"},
    {"query": "मागेल त्याला शेततळे योजनेसाठी ऑनलाइन अर्ज कसा करावा?", "lang": "mr", "loc": "Maharashtra", "crop": "General"},
    {"query": "द्राक्ष बागेत डावणी आणि भुरी रोगाचे व्यवस्थापन कसे करावे?", "lang": "mr", "loc": "Maharashtra", "crop": "Grapes"},

    # --- 7. BENGALI PROMPTS (8) ---
    {"query": "ধান চাষে সঠিক NPK সারের পরিমাণ কত দেওয়া উচিত?", "lang": "bn", "loc": "West Bengal", "crop": "Paddy"},
    {"query": "পশ্চিমবঙ্গের বাজারে আজ আলু ও ধানের মান্ডি দর কত?", "lang": "bn", "loc": "West Bengal", "crop": "Potato"},
    {"query": "কৃষক বন্ধু প্রকল্পে বার্ষিক ₹১০,০০০ টাকা পাওয়ার নিয়ম কি?", "lang": "bn", "loc": "West Bengal", "crop": "General"},
    {"query": "পাট চাষে রোগ ও পোকা দমনের জৈব উপায় কি?", "lang": "bn", "loc": "West Bengal", "crop": "Jute"},
    {"query": "পিএম কিষান সম্মান নিধি যোজনায় আধার লিঙ্ক করার নিয়ম কি?", "lang": "bn", "loc": "West Bengal", "crop": "General"},
    {"query": "আলু গাছে নাবি ধসা রোগ প্রতিরোধের ওষুধ কি?", "lang": "bn", "loc": "West Bengal", "crop": "Potato"},
    {"query": "চা বাগানে লাল মাকড়সা আক্রমণ প্রতিরোধের উপায় কি?", "lang": "bn", "loc": "West Bengal", "crop": "Tea"},
    {"query": "সর্ষে গাছে জাব পোকা দমনের কার্যকরী স্প্রে কোনটি?", "lang": "bn", "loc": "West Bengal", "crop": "Mustard"},

    # --- 8. GUJARATI PROMPTS (8) ---
    {"query": "ઘઉંના પાકમાં NPK ખાતરનું યોગ્ય પ્રમાણ શું હોવું જોઈએ?", "lang": "gu", "loc": "Gujarat", "crop": "Wheat"},
    {"query": "ઊંઝા મંડીમાં આજે જીરું અને કપાસનો બજાર ભાવ શું છે?", "lang": "gu", "loc": "Gujarat", "crop": "Cumin"},
    {"query": "આઈ-ખેડૂત પોર્ટલ પરથી કૃષિ સબસિડીનો લાભ કેવી રીતે લેવો?", "lang": "gu", "loc": "Gujarat", "crop": "General"},
    {"query": "મગફળીના પાકમાં સુકારો અને ગેરુ રોગનું નિયંત્રણ કેવી રીતે કરવું?", "lang": "gu", "loc": "Gujarat", "crop": "Groundnut"},
    {"query": "કપાસમાં ગુલાબી ઈયળના નિયંત્રણ માટે કઈ દવા છંટકાવ કરવી?", "lang": "gu", "loc": "Gujarat", "crop": "Cotton"},
    {"query": "મુખ્યમંત્રી કિસાન સહાય યોજનાનો લાભ મેળવવાની લાયકાત શું છે?", "lang": "gu", "loc": "Gujarat", "crop": "General"},
    {"query": "એરંડાના પાકમાં ખાતર આપવાની સાચી રીત કઈ છે?", "lang": "gu", "loc": "Gujarat", "crop": "Castor"},
    {"query": "રાઈના પાકમાં મોલો મશીન રોકવા માટે શું કરવું?", "lang": "gu", "loc": "Gujarat", "crop": "Mustard"},

    # --- 9. PUNJABI PROMPTS (8) ---
    {"query": "ਕਣਕ ਦੀ ਫਸਲ ਲਈ NPK ਖਾਦਾਂ ਦੀ ਸਹੀ ਮਾਤਰਾ ਕੀ ਹੈ?", "lang": "pa", "loc": "Punjab", "crop": "Wheat"},
    {"query": "ਖੰਨਾ ਅਤੇ ਲੁਧਿਆਣਾ ਮੰਡੀ ਵਿੱਚ ਅੱਜ ਕਣਕ ਦਾ ਸਰਕਾਰੀ ਭਾਅ ਕੀ ਹੈ?", "lang": "pa", "loc": "Punjab", "crop": "Wheat"},
    {"query": "ਪੀਐਮ ਕਿਸਾਨ ਯੋਜਨਾ ਦੀ ਅਗਲੀ ਕਿਸ਼ਤ ਕਿਵੇਂ ਚੈੱਕ ਕਰੀਏ?", "lang": "pa", "loc": "Punjab", "crop": "General"},
    {"query": "ਝੋਨੇ ਦੀ ਪਰਾਲੀ ਨਾ ਸਾੜਨ ਲਈ ਸਰਕਾਰੀ ਮਸ਼ੀਨਰੀ 'ਤੇ ਸਬਸਿਡੀ ਕਿਵੇਂ ਮਿਲੇਗੀ?", "lang": "pa", "loc": "Punjab", "crop": "Paddy"},
    {"query": "ਕਣਕ ਵਿੱਚ ਪੀਲੀ ਕੁੰਗੀ ਬਿਮਾਰੀ ਦਾ ਤੁਰੰਤ ਇਲਾਜ ਕੀ ਹੈ?", "lang": "pa", "loc": "Punjab", "crop": "Wheat"},
    {"query": "ਨਰਮੇ ਦੀ ਫਸਲ ਨੂੰ ਚਿੱਟੀ ਮੱਖੀ ਦੇ ਹਮਲੇ ਤੋਂ ਕਿਵੇਂ ਬਚਾਈਏ?", "lang": "pa", "loc": "Punjab", "crop": "Cotton"},
    {"query": "ਪਾਣੀ ਬਚਾਓ ਪੈਸਾ ਕਮਾਓ ਯੋਜਨਾ ਦੇ ਕੀ ਫਾਇਦੇ ਹਨ?", "lang": "pa", "loc": "Punjab", "crop": "General"},
    {"query": "ਕਮਾਦ ਦੀ ਫਸਲ ਵਿੱਚ ਸੁੰਡੀ ਦੀ ਰੋਕਥਾਮ ਲਈ ਕੀ ਛਿੜਕੀਏ?", "lang": "pa", "loc": "Punjab", "crop": "Sugarcane"},

    # --- 10. MALAYALAM PROMPTS (8) ---
    {"query": "നെല്ല് കൃഷിയിൽ ഉപയോഗിക്കേണ്ട NPK വളങ്ങളുടെ അളവ് എത്രയാണ്?", "lang": "ml", "loc": "Kerala", "crop": "Paddy"},
    {"query": "കൊച്ചി സ്പൈസ് എക്സ്ചേഞ്ചിൽ കുരുമുളകിന്റെ ഇന്നത്തെ വിപണി വില എത്ര?", "lang": "ml", "loc": "Kerala", "crop": "Pepper"},
    {"query": "പിഎം കിസാൻ ₹6000 ധനസഹായം ലഭിക്കാൻ എങ്ങനെ അപേക്ഷിക്കാം?", "lang": "ml", "loc": "Kerala", "crop": "General"},
    {"query": "തെങ്ങിന്റെ മണ്ടചീച്ചൽ രോഗം തടയാൻ എന്തുചെയ്യണം?", "lang": "ml", "loc": "Kerala", "crop": "Coconut"},
    {"query": "റബ്ബർ മരങ്ങളിലെ ഇലകൊഴിച്ചിൽ രോഗത്തിന് ഫലപ്രദമായ മരുന്ന് ഏതാണ്?", "lang": "ml", "loc": "Kerala", "crop": "Rubber"},
    {"query": "സുഭിക്ഷ കേരളം പദ്ധതി വഴി കാർഷിക വായ്പ എങ്ങനെ ലഭിക്കും?", "lang": "ml", "loc": "Kerala", "crop": "General"},
    {"query": "വാഴയിലെ വാട്ടരോഗവും തടതുരപ്പൻ പുഴുവിനെയും എങ്ങനെ നിയന്ത്രിക്കാം?", "lang": "ml", "loc": "Kerala", "crop": "Banana"},
    {"query": "ഏലക്ക കൃഷിയിലെ പേൻ ആക്രമണം തടയാൻ ചെയ്യേണ്ട കാര്യങ്ങൾ എന്ത്?", "lang": "ml", "loc": "Kerala", "crop": "Cardamom"},

    # --- 11. ODIA PROMPTS (8) ---
    {"query": "ଧାନ ଫସଲ ପାଇଁ ସଠିକ୍ NPK ସାରର ପରିମାଣ କେତେ ହେବା ଉଚିତ୍?", "lang": "or", "loc": "Odia", "crop": "Paddy"},
    {"query": "ଓଡ଼ିଶାର ମଣ୍ଡିରେ ଆଜି ଧାନର ସରକାରୀ ନିଲାମ ଦର କେତେ?", "lang": "or", "loc": "Odia", "crop": "Paddy"},
    {"query": "ପିଏମ୍ କିଷାନ ଯୋଜନାରେ ₹୬୦୦୦ ଟଙ୍କା ପାଇବା ପାଇଁ କିପରି ଆବେଦନ କରିବେ?", "lang": "or", "loc": "Odia", "crop": "General"},
    {"query": "କାଳିଆ ଯୋଜନାରେ ଚାଷୀଙ୍କୁ କେତେ ସହାୟତା ରାଶି ମିଳିଥାଏ?", "lang": "or", "loc": "Odia", "crop": "General"},
    {"query": "ମକା ଫସଲରେ ପୋକ ନିୟନ୍ତ୍ରଣ ପାଇଁ କେଉଁ ଔଷଧ ସିଞ୍ଚନ କରିବେ?", "lang": "or", "loc": "Odia", "crop": "Maize"},
    {"query": "ଆଖୁ ଫସଲରେ ଲାଲ ପଚା ରୋଗ ଦମନ ପାଇଁ ଉପାୟ କ'ଣ?", "lang": "or", "loc": "Odia", "crop": "Sugarcane"},
    {"query": "ରାଶି ଓ ବାଦାମ ଫସଲର ସୁରକ୍ଷା ପାଇଁ ଜୈବିକ ଉପାୟ କ'ଣ?", "lang": "or", "loc": "Odia", "crop": "Groundnut"},
    {"query": "ମୃତ୍ତିକା ସ୍ୱାସ୍ଥ୍ୟ କାର୍ଡ ମାଧ୍ୟମରେ ମାଟି ପରୀକ୍ଷା କିପରି କରିବେ?", "lang": "or", "loc": "Odia", "crop": "General"},

    # --- 12. ASSAMESE PROMPTS (8) ---
    {"query": "ধান খেতিত সঠিক NPK সাৰ প্ৰয়োগৰ পৰিমাণ কিমান হ'ব লাগে?", "lang": "as", "loc": "Assam", "crop": "Paddy"},
    {"query": "অসমৰ বজাৰত আজি ধান আৰু চাহ পাতৰ পাইকাৰী দৰ কিমান?", "lang": "as", "loc": "Assam", "crop": "Paddy"},
    {"query": "পিএম কিষাণ আঁচনিৰ ₹৬০০০ টকা লাভ কৰিবলৈ আবেদন কেনেকৈ কৰিব?", "lang": "as", "loc": "Assam", "crop": "General"},
    {"query": "সৰিয়হ খেতিত মাহী পোকা প্ৰতিৰোধ কৰাৰ উপায় কি?", "lang": "as", "loc": "Assam", "crop": "Mustard"},
    {"query": "চাহ বাগিচাত ৰঙা মকৰা প্ৰতিৰোধ কৰিবলৈ কি দৰৱ স্প্ৰে কৰিব?", "lang": "as", "loc": "Assam", "crop": "Tea"},
    {"query": "মাকৈ খেতিত পোকা নিয়ন্ত্ৰণৰ বাবে জৈৱিক উপায় কি?", "lang": "as", "loc": "Assam", "crop": "Maize"},
    {"query": "মাটি পৰীক্ষাৰ বাবে ছইল হেল্থ কাৰ্ড কেনেকৈ প্ৰস্তুত কৰিব?", "lang": "as", "loc": "Assam", "crop": "General"},
    {"query": "কৃষি ঋণ ক্ৰেডিট কাৰ্ড (KCC) লাভ কৰাৰ যোগ্যতা কি?", "lang": "as", "loc": "Assam", "crop": "General"},

    # --- 13. URDU PROMPTS (8) ---
    {"query": "گندم کی فصل کے لیے این پی کے (NPK) کھاد کی صحیح مقدار کیا ہے؟", "lang": "ur", "loc": "Uttar Pradesh", "crop": "Wheat"},
    {"query": "آج منڈی میں گندم اور چاول کی تازہ ترین قیمت کیا ہے؟", "lang": "ur", "loc": "Punjab", "crop": "Wheat"},
    {"query": "پی ایم کسان اسکیم کے تحت سالانہ 6000 روپے کیسے حاصل کریں؟", "lang": "ur", "loc": "Bihar", "crop": "General"},
    {"query": "کپاس کی فصل میں کیڑوں کے حملے کو روکنے کے طریقے بتائیں؟", "lang": "ur", "loc": "Maharashtra", "crop": "Cotton"},
    {"query": "گنے کی فصل کے لیے آبپاشی کا بہترین وقت کون سا ہے؟", "lang": "ur", "loc": "Uttar Pradesh", "crop": "Sugarcane"},
    {"query": "کسان کریڈٹ کارڈ اسکیم کے فوائد اور درخواست دینے کا طریقہ کیا ہے؟", "lang": "ur", "loc": "Rajasthan", "crop": "General"},
    {"query": "سرسوں کی فصل کو بیماریوں سے بچانے کے لیے نامیاتی تدابیر کیا ہیں؟", "lang": "ur", "loc": "Haryana", "crop": "Mustard"},
    {"query": "مٹی کے تجزیہ کے لیے سوائل ہیلتھ کارڈ کیسے بنوائیں؟", "lang": "ur", "loc": "Madhya Pradesh", "crop": "General"},

    # --- 14. INTERNET LIVE SEARCH & VISION DIAGNOSIS EDGE CASES (6) ---
    {"query": "Live Mandi price of Tomato and Potato today in Lasalgaon Maharashtra", "lang": "en", "loc": "Maharashtra", "crop": "Onion", "web": True},
    {"query": "Recent government agriculture subsidy news and schemes in Punjab 2026", "lang": "en", "loc": "Punjab", "crop": "Wheat", "web": True},
    {"query": "Current weather forecast impact on Rabi crop harvesting in Haryana", "lang": "en", "loc": "Haryana", "crop": "Mustard", "web": True},
    {"query": "Diagnose crop leaf blight infection from uploaded spectral image", "lang": "en", "loc": "Punjab", "crop": "Wheat", "img": True},
    {"query": "Yellow rust leaf scan analysis MM-SSNet MobileNetV3 test", "lang": "en", "loc": "Haryana", "crop": "Wheat", "img": True},
    {"query": "Chlorosis iron deficiency leaf scan diagnostic", "lang": "en", "loc": "Tamil Nadu", "crop": "Paddy", "img": True}
]

from routers.chatbot import user_request_history

# Setup test user and farm for comprehensive regression
def get_auth_headers():
    reg_resp = client.post("/api/v1/auth/register", json={
        "full_name": "Comprehensive Tester",
        "phone_or_email": "comprehensive@agrisense.io",
        "password": "Password123!",
        "farm_name": "Comprehensive Test Farm",
        "farm_acres": 10.0,
        "crop_type": "Wheat"
    })
    token = None
    if reg_resp.status_code == 200 and "session_token" in reg_resp.json():
        token = reg_resp.json()["session_token"]
    else:
        login_resp = client.post("/api/v1/auth/login", json={
            "phone_or_email": "comprehensive@agrisense.io",
            "password": "Password123!"
        })
        token = login_resp.json()["session_token"]
    
    return {"Authorization": f"Bearer {token}"}

def test_run_100_plus_prompts_comprehensive_regression():
    """Runs 106+ distinct prompts across all 13 supported languages and logs exact empirical results."""
    headers = get_auth_headers()
    start_time = time.time()
    total_prompts = len(PROMPT_CATALOG)
    passed_count = 0
    failed_prompts = []
    lang_stats = {code: {"total": 0, "passed": 0} for code in SUPPORTED_LANGUAGES.keys()}
    web_citations_found = 0

    print(f"\n=========================================================================")
    print(f"AGRISENSE 106+ COMPREHENSIVE MULTILINGUAL & INTERNET REGRESSION TEST SUITE")
    print(f"=========================================================================\n")

    # Sample base64 image string for vision diagnosis test
    sample_base64_img = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP--------------------------------------"

    for i, test in enumerate(PROMPT_CATALOG, 1):
        # Clear rate limit window for test suite batch run
        user_request_history.clear()

        q = test["query"]
        expected_lang = test["lang"]
        loc = test["loc"]
        crop = test["crop"]
        is_web = test.get("web", False)
        is_img = test.get("img", False)

        lang_stats[expected_lang]["total"] += 1

        payload = {
            "query": q,
            "language": expected_lang,
            "location": loc,
            "crop_type": crop,
            "enable_web_search": True,
            "image_base64": sample_base64_img if is_img else None
        }

        try:
            resp = client.post("/api/v1/chatbot/chat", json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success" and data.get("answer"):
                    detected_code = data["language"]["code"]
                    answer_text = data["answer"]
                    citations = data.get("web_citations", [])
                    
                    if len(citations) > 0:
                        web_citations_found += 1

                    # Verify basic sanity of response structure
                    assert len(answer_text) > 20
                    assert "AgriSense" in answer_text or len(answer_text) > 50

                    passed_count += 1
                    lang_stats[expected_lang]["passed"] += 1
                else:
                    failed_prompts.append({"id": i, "query": q, "reason": f"Invalid response JSON schema: {data}"})
            else:
                failed_prompts.append({"id": i, "query": q, "reason": f"HTTP {resp.status_code}: {resp.text}"})
        except Exception as exc:
            failed_prompts.append({"id": i, "query": q, "reason": f"Exception: {str(exc)}"})

    total_time = round(time.time() - start_time, 2)
    success_rate = round((passed_count / total_prompts) * 100.0, 2)

    print(f"Total Prompts Executed  : {total_prompts}")
    print(f"Passed Prompts          : {passed_count}")
    print(f"Failed Prompts          : {len(failed_prompts)}")
    print(f"Empirical Accuracy Rate : {success_rate}%")
    print(f"Web Search Citations    : {web_citations_found} prompts returned live web data")
    print(f"Total Test Execution Time: {total_time} seconds\n")

    print("Language-by-Language Breakdown:")
    for code, stat in lang_stats.items():
        lang_name = SUPPORTED_LANGUAGES[code]["name"]
        t = stat["total"]
        p = stat["passed"]
        rate = round((p / t * 100.0), 1) if t > 0 else 0.0
        print(f" - [{code.upper()}] {lang_name:<12}: {p}/{t} passed ({rate}%)")

    if failed_prompts:
        print("\nFAILURE DETAILS:")
        for f in failed_prompts:
            print(f" - Prompt #{f['id']}: {f['query']} -> {f['reason']}")

    assert success_rate >= 99.0, f"System accuracy rate {success_rate}% is below required 99.0% SLA!"

def test_live_internet_connectivity_and_web_parsing():
    """Explicitly verifies live network call, snippet extraction, and DDG HTML parsing."""
    res = chatbot_service.search_internet_agricultural_data("wheat mandi price Punjab 2026", "Punjab")
    assert len(res) > 0
    assert "title" in res[0]
    assert "snippet" in res[0]
    assert "url" in res[0]
    assert res[0]["url"].startswith("http")

def test_all_13_languages_catalog_endpoint():
    """Verifies backend catalog endpoint for all 13 supported languages."""
    resp = client.get("/api/v1/chatbot/languages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["total"] == 13
