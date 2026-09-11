import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/telemetry_models.dart';

class WebSocketService {
  WebSocketChannel? _channel;
  final StreamController<TelemetryPacket> _telemetryController = StreamController<TelemetryPacket>.broadcast();
  final StreamController<bool> _connectionController = StreamController<bool>.broadcast();

  Stream<TelemetryPacket> get telemetryStream => _telemetryController.stream;
  Stream<bool> get connectionStream => _connectionController.stream;

  bool _isConnected = false;
  bool get isConnected => _isConnected;

  void connect(String wsUrl) {
    try {
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
      _isConnected = true;
      _connectionController.add(true);

      _channel!.stream.listen(
        (data) {
          final decoded = jsonDecode(data as String);
          final packet = TelemetryPacket.fromJson(decoded);
          _telemetryController.add(packet);
        },
        onError: (error) {
          _isConnected = false;
          _connectionController.add(false);
        },
        onDone: () {
          _isConnected = false;
          _connectionController.add(false);
        },
      );
    } catch (e) {
      _isConnected = false;
      _connectionController.add(false);
    }
  }

  void sendPresetCommand(String presetName) {
    if (_channel != null && _isConnected) {
      final payload = jsonEncode({
        'action': 'simulate',
        'preset': presetName,
      });
      _channel!.sink.add(payload);
    }
  }

  void disconnect() {
    _channel?.sink.close();
    _isConnected = false;
    _connectionController.add(false);
  }

  void dispose() {
    disconnect();
    _telemetryController.close();
    _connectionController.close();
  }
}
