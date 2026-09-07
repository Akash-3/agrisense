import 'dart:async';
import 'package:http/http.dart' as http;

class AppConfig {
  static String activeHost = 'agrisense.tail0d103f.ts.net:8000';
  static String? userCustomHost;

  static String get backendHttpUrl {
    String host = userCustomHost ?? activeHost;
    if (host.startsWith('http://') || host.startsWith('https://')) return host;
    if (host.contains('.ts.net') && !host.contains(':')) {
      return 'https://$host';
    }
    if (host.contains('.trycloudflare.com')) {
      return 'https://$host';
    }
    return 'http://$host';
  }

  static String get backendWsUrl {
    String host = userCustomHost ?? activeHost;
    if (host.startsWith('ws://') || host.startsWith('wss://')) return host;
    if (host.contains('.ts.net') && !host.contains(':')) {
      return 'wss://$host';
    }
    if (host.contains('.trycloudflare.com')) {
      return 'wss://$host';
    }
    return 'ws://$host';
  }

  static Future<String> resolveActiveHost() async {
    if (userCustomHost != null && userCustomHost!.isNotEmpty) {
      activeHost = userCustomHost!;
      return activeHost;
    }

    List<String> candidates = [
      'agrisense.tail0d103f.ts.net:8000',
      '172.19.18.46:8000',
      'filename-enjoying-evaluation-gear.trycloudflare.com',
      '100.126.23.88:8000',
      'agrisense.tail0d103f.ts.net',
    ];

    Completer<String> completer = Completer<String>();
    int pending = candidates.length;

    for (String host in candidates) {
      final scheme = (host.contains('.ts.net') && !host.contains(':') || host.contains('.trycloudflare.com')) ? 'https' : 'http';
      final uri = Uri.parse('$scheme://$host/api/v1/health');
      http.get(uri).timeout(const Duration(milliseconds: 2500)).then((res) {
        if (res.statusCode == 200 && !completer.isCompleted) {
          activeHost = host;
          completer.complete(host);
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
