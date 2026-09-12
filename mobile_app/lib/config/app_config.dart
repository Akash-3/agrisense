import 'dart:async';
import 'package:http/http.dart' as http;

class AppConfig {
  /// Single public AgriSense backend.
  ///
  /// Tailscale Funnel exposes the local FastAPI server on port 8000
  /// through HTTPS, so clients must NOT append :8000.
  static const String productionHost =
      'https://admin.tail4fe027.ts.net';

  /// Optional user-specified backend.
  ///
  /// Kept only if the application intentionally supports custom
  /// backend hosts.
  static String? userCustomHost;

  /// Currently active backend.
  static String activeHost = productionHost;

  /// HTTP/HTTPS backend URL.
  static String get backendHttpUrl {
    final host = userCustomHost?.trim();

    if (host == null || host.isEmpty) {
      return productionHost;
    }

    if (host.startsWith('http://') ||
        host.startsWith('https://')) {
      return host;
    }

    return 'https://$host';
  }

  /// WebSocket backend URL.
  static String get backendWsUrl {
    final host = userCustomHost?.trim();

    if (host == null || host.isEmpty) {
      return 'wss://admin.tail4fe027.ts.net';
    }

    if (host.startsWith('ws://') ||
        host.startsWith('wss://')) {
      return host;
    }

    if (host.startsWith('http://')) {
      return host.replaceFirst(
        'http://',
        'ws://',
      );
    }

    if (host.startsWith('https://')) {
      return host.replaceFirst(
        'https://',
        'wss://',
      );
    }

    return 'wss://$host';
  }

  /// Resolve the active backend.
  ///
  /// Production uses the single public Funnel endpoint.
  /// No LAN, Tailscale-IP, or legacy-host fallback is attempted.
  static Future<String> resolveActiveHost() async {
    if (userCustomHost != null &&
        userCustomHost!.trim().isNotEmpty) {
      activeHost = userCustomHost!.trim();
      return activeHost;
    }

    activeHost = productionHost;

    try {
      final uri = Uri.parse(
        '$productionHost/api/v1/health',
      );

      final response = await http
          .get(uri)
          .timeout(
            const Duration(seconds: 8),
          );

      if (response.statusCode == 200) {
        return activeHost;
      }

      return activeHost;
    } catch (_) {
      // Keep the production endpoint as the active host.
      //
      // The individual API call can report the actual connectivity
      // error to the application instead of silently switching to
      // an obsolete LAN/Tailscale endpoint.
      return activeHost;
    }
  }
}