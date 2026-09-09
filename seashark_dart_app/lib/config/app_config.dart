import 'dart:async';
import 'package:http/http.dart' as http;

class AppConfig {
  static String activeHost = '100.126.23.88:8000';
  static String? userCustomHost;

  static String get backendHttpUrl {
    String host = userCustomHost ?? activeHost;
    if (host.startsWith('http://') || host.startsWith('https://')) return host;
    return 'http://$host';
  }

  static String get backendWsUrl {
    String host = userCustomHost ?? activeHost;
    if (host.startsWith('ws://') || host.startsWith('wss://')) return host;
    return 'ws://$host';
  }

  static Future<String> resolveActiveHost() async {
    if (userCustomHost != null && userCustomHost!.isNotEmpty) {
      activeHost = userCustomHost!;
      return activeHost;
    }

    // TAILSCALE TAILNET EXCLUSIVE HOST LIST
    List<String> candidates = [
      '100.126.23.88:8000',
      'agrisense.tail0d103f.ts.net:8000',
      '172.19.17.125:8000',
    ];

    Completer<String> completer = Completer<String>();
    int pending = candidates.length;

    for (String host in candidates) {
      final uri = Uri.parse('http://$host/api/v1/health');
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
