

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // GLOBAL UNCAUGHT ERROR & CRASH GUARD
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);

    if (kDebugMode) {
      print(
        '[AGRIVISION CRASH GUARD] Captured Flutter Error: '
        '${details.exception}',
      );
    }
  };

  PlatformDispatcher.instance.onError = (error, stack) {
    if (kDebugMode) {
      print(
        '[AGRIVISION ASYNC GUARD] Captured Unhandled Async Error: $error',
      );
    }

    return true;
  };

  runApp(const AgriSenseApp());
}