/*
 * AgriSense Stationary Ground Sensor Node Firmware
 * Microcontroller: ESP32 DevKit V1
 * Sensors: 
 *   - Capacitive Soil Moisture Sensor (Analog Pin=GPIO 35)
 * Communication: Wi-Fi HTTP POST (JSON Payload to FastAPI Backend)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// --- Configuration ---
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL = "http://192.168.1.100:8000/api/v1/sensors"; // Replace with your server IP

#define SOIL_PIN 35

// Calibration values for soil sensor
const int AirValue = 3200;   // Dry soil reading
const int WaterValue = 1300; // Fully submerged in water reading

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[AgriSense] Initializing Ground Sensor Node...");

  analogReadResolution(12);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[Wi-Fi] Connected! IP Address: " + WiFi.localIP().toString());
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    int rawSoil = analogRead(SOIL_PIN);
    
    // Map raw ADC reading to 0 - 100% moisture percentage
    float moisturePct = map(rawSoil, AirValue, WaterValue, 0, 100);
    moisturePct = constrain(moisturePct, 0.0, 100.0);

    StaticJsonDocument<256> doc;
    doc["device_id"] = "ground01";
    doc["device_type"] = "ground";
    doc["soil_moisture"] = moisturePct;

    String jsonPayload;
    serializeJson(doc, jsonPayload);

    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.POST(jsonPayload);
    if (httpResponseCode > 0) {
      Serial.printf("[HTTP] Ground Node POST Response code: %d\n", httpResponseCode);
    } else {
      Serial.printf("[HTTP] POST failed, error: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  } else {
    WiFi.reconnect();
  }

  // Sample ground soil every 10 seconds
  delay(10000);
}
