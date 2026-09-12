import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/app_config.dart';

class UpdateService {
  const UpdateService();

  Future<UpdateInfo?> checkForUpdate({
    required String currentVersion,
  }) async {
    await AppConfig.resolveActiveHost();

    final uri = Uri.parse(
      '${AppConfig.backendHttpUrl}/api/v1/update/check'
      '?current_version=${Uri.encodeQueryComponent(currentVersion)}',
    );

    try {
      final response =
          await http.get(uri).timeout(const Duration(seconds: 8));

      if (response.statusCode != 200) {
        throw UpdateServiceException(
          'Update check failed (HTTP ${response.statusCode}).',
        );
      }

      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) {
        throw const UpdateServiceException(
          'Update service returned an invalid response.',
        );
      }

      return UpdateInfo.fromJson(decoded);
    } on UpdateServiceException {
      rethrow;
    } on Exception catch (e) {
      throw UpdateServiceException('Update check failed: $e');
    }
  }
}

class UpdateInfo {
  final bool hasUpdate;
  final String? latestVersion;
  final String? downloadUrl;
  final String? releaseNotes;

  const UpdateInfo({
    required this.hasUpdate,
    this.latestVersion,
    this.downloadUrl,
    this.releaseNotes,
  });

  factory UpdateInfo.fromJson(Map<String, dynamic> json) {
    return UpdateInfo(
      hasUpdate: json['has_update'] == true,
      latestVersion: json['latest_version']?.toString(),
      downloadUrl: json['download_url']?.toString(),
      releaseNotes: json['release_notes']?.toString(),
    );
  }
}

class UpdateServiceException implements Exception {
  final String message;

  const UpdateServiceException(this.message);

  @override
  String toString() => message;
}
