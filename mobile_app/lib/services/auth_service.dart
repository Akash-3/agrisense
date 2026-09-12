import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/app_config.dart';

/// Centralizes all authentication HTTP calls and session management.
class AuthService {
  const AuthService();

  static const _secureStorage = FlutterSecureStorage();
  static const _tokenKey = 'auth_session_token';
  static const _farmerDataKey = 'auth_farmer_data';

  Future<void> saveSession(String token, Map<String, dynamic> farmerData) async {
    await _secureStorage.write(key: _tokenKey, value: token);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_farmerDataKey, jsonEncode(farmerData));
  }

  Future<void> clearSession() async {
    await _secureStorage.delete(key: _tokenKey);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_farmerDataKey);
  }

  Future<Map<String, dynamic>?> getStoredFarmer() async {
    final prefs = await SharedPreferences.getInstance();
    final dataStr = prefs.getString(_farmerDataKey);
    final token = await _secureStorage.read(key: _tokenKey);
    
    if (dataStr != null && token != null) {
      try {
        return jsonDecode(dataStr) as Map<String, dynamic>;
      } catch (e) {
        // Fallthrough
      }
    }
    return null;
  }

  Future<String?> getToken() async {
    return await _secureStorage.read(key: _tokenKey);
  }

  Future<Map<String, dynamic>> login({
    required String phoneOrEmail,
    required String password,
  }) async {
    final response = await _post(
      '/api/v1/auth/login',
      {
        'phone_or_email': phoneOrEmail.trim(),
        'password': password,
      },
      timeout: const Duration(seconds: 12),
    );

    final data = _decodeSuccess(response, expectedStatus: 200);
    if (data['session_token'] != null && data['farmer'] != null) {
      await saveSession(data['session_token'], data['farmer']);
    }
    return data;
  }

  Future<Map<String, dynamic>> sendRegistrationOtp({
    required String phoneOrEmail,
    required String fullName,
  }) async {
    final response = await _post(
      '/api/v1/auth/send-otp',
      {
        'phone_or_email': phoneOrEmail.trim(),
        'full_name': fullName.trim(),
      },
      timeout: const Duration(seconds: 8),
    );

    return _decodeSuccess(response, expectedStatus: 200);
  }

  Future<Map<String, dynamic>> register({
    required String fullName,
    required String phoneOrEmail,
    required String farmName,
    required double farmAcres,
    required String password,
    String? gender,
    int? age,
    required String otpCode,
  }) async {
    final body = <String, dynamic>{
      'full_name': fullName.trim(),
      'phone_or_email': phoneOrEmail.trim(),
      'farm_name': farmName.trim(),
      'farm_acres': farmAcres,
      'password': password,
      'otp_code': otpCode.trim(),
    };

    if (gender != null && gender.trim().isNotEmpty) {
      body['gender'] = gender.trim();
    }
    if (age != null) {
      body['age'] = age;
    }

    final response = await _post(
      '/api/v1/auth/register',
      body,
      timeout: const Duration(seconds: 12),
    );

    final data = _decodeSuccess(response, expectedStatus: 200);
    return data;
  }

  Future<Map<String, dynamic>> sendPasswordResetOtp({
    required String phoneOrEmail,
  }) async {
    final response = await _post(
      '/api/v1/auth/forgot-password/send-otp',
      {'phone_or_email': phoneOrEmail.trim()},
      timeout: const Duration(seconds: 8),
    );

    return _decodeSuccess(response, expectedStatus: 200);
  }

  Future<Map<String, dynamic>> resetPassword({
    required String phoneOrEmail,
    required String newPassword,
    required String otpCode,
  }) async {
    final response = await _post(
      '/api/v1/auth/forgot-password/reset',
      {
        'phone_or_email': phoneOrEmail.trim(),
        'new_password': newPassword,
        'otp_code': otpCode.trim(),
      },
      timeout: const Duration(seconds: 10),
    );

    return _decodeSuccess(response, expectedStatus: 200);
  }

  Future<Map<String, dynamic>> ssoLogin(String provider) async {
    final normalized = provider.trim().toLowerCase();
    if (normalized != 'google' && normalized != 'microsoft') {
      throw AuthServiceException('Unsupported SSO provider: $provider');
    }

    final response = await _post(
      '/api/v1/auth/sso/$normalized',
      const {},
      timeout: const Duration(seconds: 12),
    );

    final data = _decodeSuccess(response, expectedStatus: 200);
    if (data['session_token'] != null && data['farmer'] != null) {
      await saveSession(data['session_token'], data['farmer']);
    }
    return data;
  }

  Future<Map<String, dynamic>> updateProfile({
    required String farmerId,
    required Map<String, dynamic> updates,
  }) async {
    final body = <String, dynamic>{'farmer_id': farmerId, ...updates};

    final response = await _post(
      '/api/v1/auth/profile/update',
      body,
      timeout: const Duration(seconds: 10),
    );

    return _decodeSuccess(response, expectedStatus: 200);
  }

  Future<http.Response> _post(
    String path,
    Map<String, dynamic> body, {
    required Duration timeout,
  }) async {
    await AppConfig.resolveActiveHost();
    
    final token = await getToken();
    final headers = {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };

    try {
      return await http
          .post(
            Uri.parse('${AppConfig.backendHttpUrl}$path'),
            headers: headers,
            body: jsonEncode(body),
          )
          .timeout(timeout);
    } on Exception catch (e) {
      throw AuthServiceException('Authentication request failed: $e');
    }
  }

  Map<String, dynamic> _decodeSuccess(
    http.Response response, {
    required int expectedStatus,
  }) {
    Map<String, dynamic> data;
    try {
      data = jsonDecode(response.body);
    } catch (_) {
      throw AuthServiceException(
        'Invalid response format. HTTP ${response.statusCode}.',
        statusCode: response.statusCode,
      );
    }

    if (response.statusCode != expectedStatus) {
      final detail = data['detail'] ?? data['message'];
      throw AuthServiceException(
        detail?.toString() ?? 'Server returned HTTP ${response.statusCode}.',
        statusCode: response.statusCode,
      );
    }

    if (data['status'] == 'error') {
      throw AuthServiceException(
        (data['detail'] ?? data['message'] ?? 'Authentication failed.').toString(),
        statusCode: response.statusCode,
      );
    }

    return data;
  }
}

class AuthServiceException implements Exception {
  final String message;
  final int? statusCode;

  const AuthServiceException(this.message, {this.statusCode});

  @override
  String toString() => message;
}
