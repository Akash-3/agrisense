import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/app_config.dart';

class AiService {
  const AiService();

  /// Sends a real crop image to the backend AI endpoint.
  ///
  /// A failed request throws instead of returning a fabricated diagnosis.
  Future<Map<String, dynamic>> diagnoseCropImage({
    required String cropType,
    required String imageBase64,
    String? note,
  }) async {
    await AppConfig.resolveActiveHost();

    final body = <String, dynamic>{
      'crop_type': cropType,
      'image_base64': imageBase64,
    };

    if (note != null && note.trim().isNotEmpty) {
      body['note'] = note.trim();
    }

    try {
      final response = await http
          .post(
            Uri.parse(
              '${AppConfig.backendHttpUrl}/api/v1/ai/diagnose-crop-image',
            ),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 15));

      Map<String, dynamic>? decoded;
      try {
        final value = jsonDecode(response.body);
        if (value is Map<String, dynamic>) {
          decoded = value;
        }
      } catch (_) {
        decoded = null;
      }

      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw AiServiceException(
          decoded?['detail']?.toString() ??
              decoded?['message']?.toString() ??
              'Crop AI request failed (HTTP ${response.statusCode}).',
          statusCode: response.statusCode,
        );
      }

      if (decoded == null) {
        throw const AiServiceException(
          'Crop AI returned an invalid response.',
        );
      }

      return decoded;
    } on AiServiceException {
      rethrow;
    } on Exception catch (e) {
      throw AiServiceException('Crop AI request failed: $e');
    }
  }
}

class AiServiceException implements Exception {
  final String message;
  final int? statusCode;

  const AiServiceException(this.message, {this.statusCode});

  @override
  String toString() => message;
}
