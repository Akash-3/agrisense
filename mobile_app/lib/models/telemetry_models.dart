class TelemetryPayload {
  final String deviceId;
  final String nodeType;
  final double timestamp;

  // AS7341 10-Channel Optical Counts
  final int f1_415nm;
  final int f2_445nm;
  final int f3_480nm;
  final int f4_515nm;
  final int f5_555nm;
  final int f6_590nm;
  final int f7_630nm;
  final int f8_680nm;
  final int clearChannel;
  final int nir_885nm;

  // Environmental & Edaphic Hydration (Nullable when sensors are disconnected)
  final double? soilMoistureVwc;
  final double? temperatureC;
  final double? humidityPct;
  final double? smokePpm;

  // Real Hardware Sensor Health Status Flags
  final String soilStatus;
  final String dhtStatus;
  final String mq135Status;

  TelemetryPayload({
    required this.deviceId,
    required this.nodeType,
    required this.timestamp,
    required this.f1_415nm,
    required this.f2_445nm,
    required this.f3_480nm,
    required this.f4_515nm,
    required this.f5_555nm,
    required this.f6_590nm,
    required this.f7_630nm,
    required this.f8_680nm,
    required this.clearChannel,
    required this.nir_885nm,
    this.soilMoistureVwc,
    this.temperatureC,
    this.humidityPct,
    this.smokePpm,
    this.soilStatus = 'ONLINE',
    this.dhtStatus = 'ONLINE',
    this.mq135Status = 'ONLINE',
  });

  factory TelemetryPayload.fromJson(Map<String, dynamic> json) {
    return TelemetryPayload(
      deviceId: json['device_id'] ?? 'AGRI-DRONE-PAYLOAD-01',
      nodeType: json['node_type'] ?? 'aerial_drone',
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
      f1_415nm: json['f1_415nm'] ?? 450,
      f2_445nm: json['f2_445nm'] ?? 680,
      f3_480nm: json['f3_480nm'] ?? 920,
      f4_515nm: json['f4_515nm'] ?? 1450,
      f5_555nm: json['f5_555nm'] ?? 2800,
      f6_590nm: json['f6_590nm'] ?? 1600,
      f7_630nm: json['f7_630nm'] ?? 980,
      f8_680nm: json['f8_680nm'] ?? 520,
      clearChannel: json['clear_channel'] ?? 12400,
      nir_885nm: json['nir_885nm'] ?? 6400,
      soilMoistureVwc: (json['soil_moisture_vwc'] as num?)?.toDouble(),
      temperatureC: (json['temperature_c'] as num?)?.toDouble(),
      humidityPct: (json['humidity_pct'] as num?)?.toDouble(),
      smokePpm: (json['smoke_ppm'] as num?)?.toDouble(),
      soilStatus: json['soil_status'] ?? 'ONLINE',
      dhtStatus: json['dht_status'] ?? 'ONLINE',
      mq135Status: json['mq135_status'] ?? 'ONLINE',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'device_id': deviceId,
      'node_type': nodeType,
      'timestamp': timestamp,
      'f1_415nm': f1_415nm,
      'f2_445nm': f2_445nm,
      'f3_480nm': f3_480nm,
      'f4_515nm': f4_515nm,
      'f5_555nm': f5_555nm,
      'f6_590nm': f6_590nm,
      'f7_630nm': f7_630nm,
      'f8_680nm': f8_680nm,
      'clear_channel': clearChannel,
      'nir_885nm': nir_885nm,
      'soil_moisture_vwc': soilMoistureVwc,
      'temperature_c': temperatureC,
      'humidity_pct': humidityPct,
      'smoke_ppm': smokePpm,
      'soil_status': soilStatus,
      'dht_status': dhtStatus,
      'mq135_status': mq135Status,
    };
  }
}

class AIDiagnosticResult {
  final String status;
  final double pathogenRiskPct;
  final double cropHealthIndex;
  final double preSymptomaticLeadDays;
  final String recommendedAction;
  final String? hazardAlert;
  final String? sensorFaultAlert;

  AIDiagnosticResult({
    required this.status,
    required this.pathogenRiskPct,
    required this.cropHealthIndex,
    required this.preSymptomaticLeadDays,
    required this.recommendedAction,
    this.hazardAlert,
    this.sensorFaultAlert,
  });

  factory AIDiagnosticResult.fromJson(Map<String, dynamic> json) {
    return AIDiagnosticResult(
      status: json['status'] ?? 'HEALTHY',
      pathogenRiskPct: (json['pathogen_risk_pct'] as num?)?.toDouble() ?? 5.0,
      cropHealthIndex: (json['crop_health_index'] as num?)?.toDouble() ?? 82.0,
      preSymptomaticLeadDays: (json['pre_symptomatic_lead_days'] as num?)?.toDouble() ?? 0.0,
      recommendedAction: json['recommended_action'] ?? '',
      hazardAlert: json['hazard_alert'],
      sensorFaultAlert: json['sensor_fault_alert'],
    );
  }
}

class TelemetryPacket {
  final TelemetryPayload telemetry;
  final AIDiagnosticResult aiDiagnosis;

  TelemetryPacket({required this.telemetry, required this.aiDiagnosis});

  factory TelemetryPacket.fromJson(Map<String, dynamic> json) {
    return TelemetryPacket(
      telemetry: TelemetryPayload.fromJson(json['telemetry'] ?? {}),
      aiDiagnosis: AIDiagnosticResult.fromJson(json['ai_diagnosis'] ?? {}),
    );
  }
}
