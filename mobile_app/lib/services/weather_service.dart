import 'dart:convert';

import 'package:http/http.dart' as http;

class WeatherService {
  const WeatherService();

  Future<WeatherResult> getCurrentWeather({
    required double latitude,
    required double longitude,
  }) async {
    final uri = Uri.https(
      'api.open-meteo.com',
      '/v1/forecast',
      <String, String>{
        'latitude': latitude.toString(),
        'longitude': longitude.toString(),
        'current': 'temperature_2m,weather_code',
      },
    );

    try {
      final response =
          await http.get(uri).timeout(const Duration(seconds: 8));

      if (response.statusCode != 200) {
        throw WeatherServiceException(
          'Weather request failed (HTTP ${response.statusCode}).',
        );
      }

      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) {
        throw const WeatherServiceException(
          'Weather service returned an invalid response.',
        );
      }

      final current = decoded['current'];
      if (current is! Map<String, dynamic>) {
        throw const WeatherServiceException(
          'Current weather data is unavailable.',
        );
      }

      final temperature = (current['temperature_2m'] as num?)?.toDouble();
      final weatherCode = (current['weather_code'] as num?)?.toInt();

      if (temperature == null || weatherCode == null) {
        throw const WeatherServiceException(
          'Current weather data is incomplete.',
        );
      }

      return WeatherResult(
        temperatureCelsius: temperature,
        weatherCode: weatherCode,
      );
    } on WeatherServiceException {
      rethrow;
    } on Exception catch (e) {
      throw WeatherServiceException('Weather request failed: $e');
    }
  }
}

class WeatherResult {
  final double temperatureCelsius;
  final int weatherCode;

  const WeatherResult({
    required this.temperatureCelsius,
    required this.weatherCode,
  });
}

class WeatherServiceException implements Exception {
  final String message;

  const WeatherServiceException(this.message);

  @override
  String toString() => message;
}
