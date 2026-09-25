import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';

import 'auth_service.dart';

class ChatbotService {
  const ChatbotService();

  Future<List<Map<String, dynamic>>> fetchSupportedLanguages() async {
    await AppConfig.resolveActiveHost();
    try {
      final response = await http
          .get(Uri.parse('${AppConfig.backendHttpUrl}/api/v1/chatbot/languages'))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['status'] == 'success' && data['languages'] is List) {
          return List<Map<String, dynamic>>.from(data['languages']);
        }
      }
    } catch (e) {
      print("[ChatbotService] Error fetching languages: $e");
    }
    return [
      {"code": "auto", "name": "Auto Language", "native": "🌐 Auto", "flag": "🌐"},
      {"code": "hi", "name": "Hindi", "native": "हिंदी", "flag": "🇮🇳"},
      {"code": "en", "name": "English", "native": "English", "flag": "🇬🇧"},
      {"code": "ta", "name": "Tamil", "native": "தமிழ்", "flag": "🇮🇳"},
      {"code": "te", "name": "Telugu", "native": "తెలుగు", "flag": "🇮🇳"},
      {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ", "flag": "🇮🇳"},
      {"code": "mr", "name": "Marathi", "native": "मराठी", "flag": "🇮🇳"},
      {"code": "bn", "name": "Bengali", "native": "বাংলা", "flag": "🇮🇳"},
      {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી", "flag": "🇮🇳"},
      {"code": "pa", "name": "Punjabi", "native": "ਪੰਜਾਬੀ", "flag": "🇮🇳"},
      {"code": "ml", "name": "Malayalam", "native": "മലയാളം", "flag": "🇮🇳"},
      {"code": "or", "name": "Odia", "native": "ଓଡ଼ିଆ", "flag": "🇮🇳"}
    ];
  }

  Future<List<String>> fetchSuggestions({String? location, String? crop}) async {
    await AppConfig.resolveActiveHost();
    try {
      final loc = Uri.encodeComponent(location ?? 'India');
      final cr = Uri.encodeComponent(crop ?? 'Wheat & Paddy');
      final response = await http
          .get(Uri.parse('${AppConfig.backendHttpUrl}/api/v1/chatbot/suggestions?location=$loc&crop=$cr'))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['status'] == 'success' && data['suggestions'] is List) {
          return List<String>.from(data['suggestions']);
        }
      }
    } catch (e) {
      print("[ChatbotService] Error fetching suggestions: $e");
    }
    return [
      "📊 What is today's Mandi price for Wheat?",
      "🌱 Recommended NPK dose for my crop?",
      "🐛 Prevent leaf blight and yellow rust outbreak?",
      "🏛️ How to register for PM-KISAN scheme?"
    ];
  }

  Future<Map<String, dynamic>> sendChatMessage({
    required String query,
    String language = "auto",
    String? location,
    double? latitude,
    double? longitude,
    String? cropType,
    int? farmId,
    String? imageBase64,
    bool enableWebSearch = true,
  }) async {
    await AppConfig.resolveActiveHost();

    final token = await const AuthService().getToken();

    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }

    final body = <String, dynamic>{
      'query': query,
      'language': language,
      'location': location ?? 'India',
      'latitude': latitude,
      'longitude': longitude,
      'crop_type': cropType ?? 'Wheat & Paddy',
      'farm_id': farmId,
      'image_base64': imageBase64,
      'enable_web_search': enableWebSearch,
    };

    try {
      final response = await http
          .post(
            Uri.parse('${AppConfig.backendHttpUrl}/api/v1/chatbot/chat'),
            headers: headers,
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 20));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data is Map<String, dynamic>) {
          return data;
        }
      } else if (response.statusCode == 401) {
        return {
          "status": "error",
          "answer": "🔒 Authentication required. Please sign in to ask AgriSense AI.",
          "language": {"code": "en", "name": "English", "native": "English", "flag": "🇬🇧"},
          "web_search_enabled": enableWebSearch,
          "web_citations": []
        };
      }
      throw Exception('HTTP ${response.statusCode}: ${response.body}');
    } catch (e) {
      print("[ChatbotService] Query error: $e");
      return {
        "status": "error",
        "answer": "⚠️ Unable to connect to AgriSense AI server. Please check your internet connection.",
        "language": {"code": "en", "name": "English", "native": "English", "flag": "🇬🇧"},
        "web_search_enabled": enableWebSearch,
        "web_citations": []
      };
    }
  }
}
