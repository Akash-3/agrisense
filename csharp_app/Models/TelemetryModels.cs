using System;
using System.Text.Json.Serialization;

namespace AgriSenseGCS.Models
{
    public class TelemetryPayload
    {
        [JsonPropertyName("device_id")]
        public string DeviceId { get; set; } = "AGRI-DRONE-PAYLOAD-01";

        [JsonPropertyName("node_type")]
        public string NodeType { get; set; } = "aerial_drone";

        [JsonPropertyName("timestamp")]
        public double Timestamp { get; set; }

        [JsonPropertyName("f1_415nm")]
        public int F1_415nm { get; set; }

        [JsonPropertyName("f2_445nm")]
        public int F2_445nm { get; set; }

        [JsonPropertyName("f3_480nm")]
        public int F3_480nm { get; set; }

        [JsonPropertyName("f4_515nm")]
        public int F4_515nm { get; set; }

        [JsonPropertyName("f5_555nm")]
        public int F5_555nm { get; set; }

        [JsonPropertyName("f6_590nm")]
        public int F6_590nm { get; set; }

        [JsonPropertyName("f7_630nm")]
        public int F7_630nm { get; set; }

        [JsonPropertyName("f8_680nm")]
        public int F8_680nm { get; set; }

        [JsonPropertyName("clear_channel")]
        public int ClearChannel { get; set; }

        [JsonPropertyName("nir_885nm")]
        public int Nir_885nm { get; set; }

        [JsonPropertyName("soil_moisture_vwc")]
        public double SoilMoistureVwc { get; set; }

        [JsonPropertyName("temperature_c")]
        public double TemperatureC { get; set; }

        [JsonPropertyName("humidity_pct")]
        public double HumidityPct { get; set; }

        [JsonPropertyName("smoke_ppm")]
        public double SmokePpm { get; set; }
    }

    public class AIDiagnosticResult
    {
        [JsonPropertyName("status")]
        public string Status { get; set; } = "HEALTHY";

        [JsonPropertyName("pathogen_risk_pct")]
        public double PathogenRiskPct { get; set; }

        [JsonPropertyName("crop_health_index")]
        public double CropHealthIndex { get; set; }

        [JsonPropertyName("pre_symptomatic_lead_days")]
        public double PreSymptomaticLeadDays { get; set; }

        [JsonPropertyName("recommended_action")]
        public string RecommendedAction { get; set; } = string.Empty;

        [JsonPropertyName("hazard_alert")]
        public string? HazardAlert { get; set; }
    }

    public class TelemetryPacket
    {
        [JsonPropertyName("telemetry")]
        public TelemetryPayload Telemetry { get; set; } = new();

        [JsonPropertyName("ai_diagnosis")]
        public AIDiagnosticResult AiDiagnosis { get; set; } = new();
    }
}
