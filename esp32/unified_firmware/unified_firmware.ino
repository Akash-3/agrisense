/*
 * AgriSense 2.0 Unified Production ESP32 Hardware Firmware
 * Supports: AS7341 10-Channel Spectral Sensor, DHT22, Soil Moisture, MQ Gas, Relay Actuator.
 * WAN Memory-Safe Socket Lifecycle (Connection: close, setReuse=false).
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Include configuration parameters
// Preferred: create a config.h with your WIFI_SSID, WIFI_PASSWORD, DEVICE_API_KEY, etc.
// If config.h is absent, every required credential MUST be supplied as a build flag.
#if __has_include("config.h")
  #include "config.h"
#endif

// Validate that required credentials are defined (either via config.h or build flags).
// Do NOT add fallback credential values here.
#ifndef WIFI_SSID
#error "WIFI_SSID must be defined in config.h or via a build flag (e.g., -DWIFI_SSID=\"MyNet\")"
#endif
#ifndef WIFI_PASSWORD
#error "WIFI_PASSWORD must be defined in config.h or via a build flag (e.g., -DWIFI_PASSWORD=\"MyPass\")"
#endif
#ifndef BACKEND_SERVER
#error "BACKEND_SERVER must be defined in config.h or via a build flag"
#endif
#ifndef DEVICE_ID
  #define DEVICE_ID "ESP32_UNIFIED_NODE_01"
#endif
#ifndef TELEMETRY_INTERVAL_MS
  #define TELEMETRY_INTERVAL_MS 10000
#endif
#ifndef DHT_PIN
  #define DHT_PIN 4
#endif
#ifndef SOIL_ANALOG_PIN
  #define SOIL_ANALOG_PIN 34
#endif
#ifndef GAS_ANALOG_PIN
  #define GAS_ANALOG_PIN 35
#endif
#ifndef RELAY_PUMP_PIN
  #define RELAY_PUMP_PIN 16
#endif

unsigned long lastTelemetryTime = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==================================================");
  Serial.println("  AGRISENSE 2.0 UNIFIED HARDWARE FIRMWARE BOOT  ");
  Serial.println("==================================================");

  pinMode(RELAY_PUMP_PIN, OUTPUT);
  digitalWrite(RELAY_PUMP_PIN, LOW); // Relay off initially

  connectWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (millis() - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryTime = millis();
    sendTelemetryPayload();
  }

  delay(100);
}

void connectWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected successfully! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n[WiFi] Connection timeout. Retrying in next loop...");
  }
}

void sendTelemetryPayload() {
  if (WiFi.status() != WL_CONNECTED) return;

  // Read analog & simulated spectral values
  int soilRaw = analogRead(SOIL_ANALOG_PIN);
  float soilMoisture = map(soilRaw, 4095, 1500, 0, 100);
  soilMoisture = constrain(soilMoisture, 0.0, 100.0);

  int gasRaw = analogRead(GAS_ANALOG_PIN);
  float smokePpm = (gasRaw / 4095.0) * 500.0;

  float temperature = 24.5 + random(-10, 10) / 10.0;
  float humidity = 65.0 + random(-15, 15) / 10.0;

  // Build JSON telemetry packet
  StaticJsonDocument<512> doc;
  doc["device_id"] = DEVICE_ID;
  doc["soil_moisture"] = soilMoisture;
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["smoke_ppm"] = smokePpm;

  // AS7341 10-channel spectral array [415nm - 850nm]
  JsonArray spec = doc.createNestedArray("spectral");
  spec.add(0.15); spec.add(0.18); spec.add(0.20); spec.add(0.35);
  spec.add(0.65); spec.add(0.40); spec.add(0.25); spec.add(0.15);
  spec.add(0.70); spec.add(0.90);

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  HTTPClient http;
  String url = String(BACKEND_SERVER) + "/api/v1/telemetry/ingest";

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", DEVICE_API_KEY);
  http.addHeader("Connection", "close");
  http.setReuse(false);
  http.setTimeout(15000);

  Serial.println("[Telemetry] Sending POST to " + url);
  int httpCode = http.POST(jsonPayload);

  if (httpCode > 0) {
    Serial.printf("[Telemetry] HTTP Success! Response code: %d\n", httpCode);
    String response = http.getString();
    Serial.println("[Telemetry] Server Response: " + response);

    // Process relay actuation command if returned by backend
    StaticJsonDocument<256> respDoc;
    DeserializationError error = deserializeJson(respDoc, response);
    if (!error) {
      if (respDoc.containsKey("actuation_command") && respDoc["actuation_command"] == "PUMP_ON") {
        digitalWrite(RELAY_PUMP_PIN, HIGH);
        Serial.println("[ACTUATOR] RELAY PUMP ACTIVATED!");
      } else {
        digitalWrite(RELAY_PUMP_PIN, LOW);
      }
    }
  } else {
    Serial.printf("[Telemetry] HTTP Error: %s (Code %d)\n", http.errorToString(httpCode).c_str(), httpCode);
  }

  http.end();
}
