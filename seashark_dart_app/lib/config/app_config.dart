import 'dart:async';
import 'package:http/http.dart' as http;

class AppConfig {
  static String activeHost = 'https://agrisense.tail0d103f.ts.net';
  static String? userCustomHost;

  static String get backendHttpUrl {
    String host = userCustomHost ?? activeHost;
    if (host.startsWith('http://') || host.startsWith('https://')) return host;
    if (host.contains('agrisense.tail0d103f.ts.net') && !host.contains(':8000')) {
      return 'https://$host';
    }
    return 'http://$host';
  }

  static String get backendWsUrl {
    String host = userCustomHost ?? activeHost;
    if (host.startsWith('ws://') || host.startsWith('wss://')) {
      return host;
    }
    if (host.startsWith('http://')) {
      return host.replaceFirst('http://', 'ws://');
    }
    if (host.startsWith('https://')) {
      return host.replaceFirst('https://', 'wss://');
    }
    if (host.contains('agrisense.tail0d103f.ts.net') && !host.contains(':8000')) {
      return 'wss://$host';
    }
    return 'ws://$host';
  }

  static Future<String> resolveActiveHost() async {
    if (userCustomHost != null && userCustomHost!.isNotEmpty) {
      activeHost = userCustomHost!;
      return activeHost;
    }

    // EXCLUSIVE TAILNET DOMAIN & TAILNET IP CANDIDATES (NO CLOUDFLARE)
    List<String> candidates = [
      'https://agrisense.tail0d103f.ts.net',
      'http://100.126.23.88:8000',
      'http://agrisense.tail0d103f.ts.net:8000',
      'http://172.19.17.125:8000',
    ];

    Completer<String> completer = Completer<String>();
    int pending = candidates.length;

    for (String url in candidates) {
      final uri = Uri.parse('$url/api/v1/health');
      http.get(uri).timeout(const Duration(milliseconds: 3500)).then((res) {
        if (res.statusCode == 200 && !completer.isCompleted) {
          activeHost = url;
          completer.complete(url);
        } else {
          pending--;
          if (pending <= 0 && !completer.isCompleted) {
            completer.complete(activeHost);
          }
        }
      }).catchError((_) {
        pending--;
        if (pending <= 0 && !completer.isCompleted) {
          completer.complete(activeHost);
        }
      });
    }

    return completer.future;
  }
}

