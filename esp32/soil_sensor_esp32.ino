/*
 * AgriSense ESP32 Soil Moisture Sensor Node Firmware
 * Board: ESP32-WROOM-32 30-Pin USB-C DevKit
 * Sensor: Capacitive Soil Moisture Sensor v1.2 / Analog Moisture Module
 * 
 * Hardware Connections:
 *   - Sensor VCC  -> ESP32 3V3 (or VIN/5V)
 *   - Sensor GND  -> ESP32 GND
 *   - Sensor AOUT -> ESP32 D34 (GPIO 34 - ADC1_CH6)
 */

#include <WiFi.h>
#include <HTTPClient.h>

// ==================== CONFIGURATION ====================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";       // Replace with your Wi-Fi name
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";   // Replace with your Wi-Fi password

// Server Endpoint (Replace with your Laptop/Server IP address or Cloudflare URL)
// Example Local IP: "http://192.168.1.100:8000/api/v1/telemetry/ingest"
// Example Cloudflare: "https://your-tunnel.trycloudflare.com/api/v1/telemetry/ingest"
const char* SERVER_URL = "http://192.168.1.100:8000/api/v1/telemetry/ingest";

const char* DEVICE_ID  = "ESP32_SOIL_NODE_01";

#define SOIL_PIN 34 // GPIO 34 (D34 on 30-pin board)

// Calibration Constants (12-bit ADC: 0 - 4095)
// Measure in air (dry) vs submerged in water (wet) using Serial Monitor
const int AirValue   = 3200; // Sensor in dry air (0% moisture)
const int WaterValue = 1200; // Sensor submerged in water (100% moisture)

// Read intervals
const unsigned long SEND_INTERVAL_MS = 5000; // Send telemetry every 5 seconds
unsigned long lastSendTime = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println();
  Serial.println("==================================================");
  Serial.println("   🌱 AgriSense ESP32 Soil Sensor Node Booting   ");
  Serial.println("==================================================");

  // Configure ADC resolution (12-bit = 0-4095 range on ESP32)
  analogReadResolution(12);
  pinMode(SOIL_PIN, INPUT);

  // Connect to Wi-Fi
  Serial.print("[Wi-Fi] Connecting to network: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("[Wi-Fi] Connected successfully!");
  Serial.print("[Wi-Fi] IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.println("==================================================");
}

// Multi-sample ADC filter to stabilize analog noise
int readAveragedAnalog(int pin, int samples = 10) {
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delay(10);
  }
  return (int)(sum / samples);
}

void sendTelemetry(float soilMoisturePct, int rawADC) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[Wi-Fi] Reconnecting...");
    WiFi.reconnect();
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  // Construct JSON payload string without needing external libraries
  char jsonBuffer[256];
  snprintf(jsonBuffer, sizeof(jsonBuffer),
           "{\"device_id\":\"%s\",\"soil_moisture\":%.1f,\"temperature\":26.5,\"humidity\":62.0,\"smoke_ppm\":80.0}",
           DEVICE_ID, soilMoisturePct);

  Serial.print("[HTTP] Outgoing Payload: ");
  Serial.println(jsonBuffer);

  int httpResponseCode = http.POST(jsonBuffer);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.printf("[HTTP] Success! Server Response Code: %d\n", httpResponseCode);
    Serial.print("[HTTP] Response Body: ");
    Serial.println(response);
  } else {
    Serial.printf("[HTTP] Error sending POST: %s (Code: %d)\n",
                  http.errorToString(httpResponseCode).c_str(), httpResponseCode);
  }

  http.end();
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - lastSendTime >= SEND_INTERVAL_MS) {
    lastSendTime = currentMillis;

    int rawADC = readAveragedAnalog(SOIL_PIN, 10);
    
    // Map raw ADC to 0.0% - 100.0% moisture percentage
    float moisturePct = (float)map(rawADC, AirValue, WaterValue, 0, 100);
    moisturePct = constrain(moisturePct, 0.0f, 100.0f);

    Serial.println("--------------------------------------------------");
    Serial.printf("[SENSOR] Raw ADC Value (D34): %d | Soil Moisture: %.1f%%\n", rawADC, moisturePct);

    // Dispatch telemetry payload to AgriSense backend
    sendTelemetry(moisturePct, rawADC);
  }
}
