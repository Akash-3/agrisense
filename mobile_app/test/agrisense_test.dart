import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:agrisense_seashark_app/models/telemetry_models.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('AgriSense Telemetry Tests', () {
    test('TelemetryPacket parses valid JSON correctly', () {
      final json = {
        'telemetry': {
          'device_id': 'sensor-1',
          'temperature_c': 28.5,
          'humidity_pct': 60.0,
        },
        'ai_diagnosis': {
          'status': 'BLIGHT_DETECTED'
        }
      };
      
      final packet = TelemetryPacket.fromJson(json);
      expect(packet.telemetry.deviceId, 'sensor-1');
      expect(packet.telemetry.temperatureC, 28.5);
      expect(packet.telemetry.humidityPct, 60.0);
      expect(packet.telemetry.soilMoistureVwc, isNull);
      expect(packet.aiDiagnosis.status, 'BLIGHT_DETECTED');
    });

    test('Missing telemetry values default to null (N/A)', () {
      final json = {
        'telemetry': {
          'device_id': 'sensor-1'
        }
      };
      
      final packet = TelemetryPacket.fromJson(json);
      expect(packet.telemetry.temperatureC, isNull);
      expect(packet.telemetry.humidityPct, isNull);
      expect(packet.telemetry.soilMoistureVwc, isNull);
      expect(packet.telemetry.smokePpm, isNull);
    });
  });

  group('Settings Persistence Tests', () {
    test('Settings write to SharedPreferences', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      
      await prefs.setBool('pref_useCelsius', false);
      expect(prefs.getBool('pref_useCelsius'), isFalse);
      
      await prefs.setBool('pref_autoSync', true);
      expect(prefs.getBool('pref_autoSync'), isTrue);
    });
  });
}
