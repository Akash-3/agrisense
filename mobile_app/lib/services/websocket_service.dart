import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/telemetry_models.dart';

class WebSocketService {
  WebSocketChannel? _channel;
  final StreamController<TelemetryPacket> _telemetryController = StreamController<TelemetryPacket>.broadcast();
  final StreamController<bool> _connectionController = StreamController<bool>.broadcast();

  Stream<TelemetryPacket> get telemetryStream => _telemetryController.stream;
  Stream<bool> get connectionStream => _connectionController.stream;

  bool _isConnected = false;
  bool get isConnected => _isConnected;
  
  String? _wsUrl;
  Timer? _reconnectTimer;
  bool _isDisposed = false;

  Future<void> connect(String wsUrl) async {
    _wsUrl = wsUrl;
    
    // Check if auto-sync is allowed by preferences
    final prefs = await SharedPreferences.getInstance();
    final autoSync = prefs.getBool('pref_autoSync') ?? true;
    if (!autoSync) {
      return;
    }
    
    _connectInternal();
  }
  
  void _handleDisconnect() {
    if (_isDisposed) return;
    
    _isConnected = false;
    _connectionController.add(false);
    _channel?.sink.close();
    _channel = null;
    
    _scheduleReconnect();
  }
  
  int _reconnectDelaySeconds = 5;

  void _scheduleReconnect() {
    if (_isDisposed) return;
    
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: _reconnectDelaySeconds), () async {
      // Exponential backoff logic, bounded at 60 seconds
      _reconnectDelaySeconds = (_reconnectDelaySeconds * 2).clamp(5, 60);

      final prefs = await SharedPreferences.getInstance();
      final autoSync = prefs.getBool('pref_autoSync') ?? true;
      if (autoSync) {
        _connectInternal();
      }
    });
  }

  void _connectInternal() {
    if (_isDisposed || _wsUrl == null) return;
    if (_isConnected && _channel != null) return;
    
    try {
      _channel?.sink.close();
      _channel = WebSocketChannel.connect(Uri.parse(_wsUrl!));
      
      _isConnected = true;
      _connectionController.add(true);
      _reconnectDelaySeconds = 5; // Reset on successful connection attempt

      _channel!.stream.listen(
        (data) {
          try {
            final decoded = jsonDecode(data as String);
            final packet = TelemetryPacket.fromJson(decoded);
            _telemetryController.add(packet);
          } catch (_) {}
        },
        onError: (error) => _handleDisconnect(),
        onDone: () => _handleDisconnect(),
      );
    } catch (e) {
      _handleDisconnect();
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
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _channel = null;
    _isConnected = false;
    _connectionController.add(false);
  }

  void dispose() {
    _isDisposed = true;
    disconnect();
    _telemetryController.close();
    _connectionController.close();
  }
}
