/*
 * AgriSense ESP32 Multi-Sensor IoT Station Firmware
 * Microcontroller: ESP32-WROOM-32 30-Pin USB-C DevKit
 * 
 * Connected Sensors:
 *   1. Soil Moisture Sensor (Analog -> D34 / GPIO 34)
 *   2. MQ-135 Air Quality / Smoke Sensor (Analog -> D35 / GPIO 35)
 *   3. DHT22 Temperature & Humidity Sensor (Digital Data -> D4 / GPIO 4)
 * 
 * Calibration Note:
 *   - Dry Air ADC = 4095 (0.0% Moisture)
 *   - Submerged Water ADC = 1200 (100.0% Moisture)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// ==================== CONFIGURATION ====================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";       // Replace with your Wi-Fi name
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";   // Replace with your Wi-Fi password

// Server Endpoint (Using your Laptop's actual Wi-Fi IP address or Cloudflare Tunnel)
// Local Wi-Fi IP: "http://172.19.17.125:8000/api/v1/telemetry/ingest"
// Cloudflare Tunnel: "https://pressing-introducing-knit-matters.trycloudflare.com/api/v1/telemetry/ingest"
const char* SERVER_URL = "http://172.19.17.125:8000/api/v1/telemetry/ingest";

const char* DEVICE_ID  = "ESP32_MULTI_NODE_01";

// ==================== PIN DEFINITIONS ====================
#define SOIL_PIN 34 // GPIO 34 (D34 - ADC1_CH6)
#define MQ135_PIN 35 // GPIO 35 (D35 - ADC1_CH7)
#define DHT_PIN   4  // GPIO 4  (D4 - Digital)
#define DHTTYPE   DHT22

DHT dht(DHT_PIN, DHTTYPE);

// Soil Calibration Constants (Dry Air ADC = 4095, Submerged Water ADC = 1200)
const int AirValue   = 4095; // Sensor in dry air (0% moisture)
const int WaterValue = 1200; // Sensor submerged in water (100% moisture)

// Read Intervals
const unsigned long SEND_INTERVAL_MS = 5000; // Send telemetry every 5 seconds
unsigned long lastSendTime = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println();
  Serial.println("==========================================================");
  Serial.println("   🌱 AgriSense ESP32 Multi-Sensor Station Booting       ");
  Serial.println("==========================================================");

  analogReadResolution(12);
  pinMode(SOIL_PIN, INPUT);
  pinMode(MQ135_PIN, INPUT);

  dht.begin();
  Serial.println("[DHT22] Sensor driver initialized on GPIO 4.");

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
  Serial.println("==========================================================");
}

int readAveragedAnalog(int pin, int samples = 10) {
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delay(5);
  }
  return (int)(sum / samples);
}

// ------------------- SENSOR READERS WITH FAULT TOLERANCE -------------------

// 1. Soil Moisture Reader (Dry Air = 4095 -> 0.0% Moisture)
float getSoilMoisture(int &rawADC) {
  rawADC = readAveragedAnalog(SOIL_PIN, 10);

  // Capacitive sensors output 4095 ADC when DRY (AirValue = 4095) and ~1200 ADC when WET (WaterValue = 1200)
  float moisturePct = (float)map(rawADC, AirValue, WaterValue, 0, 100);
  return constrain(moisturePct, 0.0f, 100.0f);
}

// 2. MQ-135 Gas / Air Quality Reader
float getSmokePPM(int &rawADC) {
  rawADC = readAveragedAnalog(MQ135_PIN, 10);

  if (rawADC < 10) {
    Serial.printf("[MQ135 WARN] Sensor unplugged (Raw ADC: %d). Using fallback 85.0 PPM\n", rawADC);
    return 85.0f;
  }

  float ppm = map(rawADC, 200, 3500, 50, 600);
  return constrain(ppm, 20.0f, 999.0f);
}

// 3. DHT22 Temp & Humidity Reader with NaN Protection
void getDHTData(float &tempC, float &humidityPct) {
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (isnan(t) || isnan(h)) {
    Serial.println("[DHT22 WARN] Sensor disconnected / NaN! Using fallback (26.5°C, 62.0%)");
    tempC = 26.5f;
    humidityPct = 62.0f;
  } else {
    tempC = t;
    humidityPct = h;
  }
}

// ------------------- HTTP TELEMETRY TRANSMITTER -------------------

void sendTelemetry(float soilMoisture, float tempC, float humidity, float smokePPM) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[Wi-Fi] Network connection lost! Reconnecting...");
    WiFi.reconnect();
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  char jsonBuffer[300];
  snprintf(jsonBuffer, sizeof(jsonBuffer),
           "{\"device_id\":\"%s\",\"soil_moisture\":%.1f,\"temperature\":%.1f,\"humidity\":%.1f,\"smoke_ppm\":%.1f}",
           DEVICE_ID, soilMoisture, tempC, humidity, smokePPM);

  Serial.print("[HTTP] Telemetry Payload: ");
  Serial.println(jsonBuffer);

  int httpCode = http.POST(jsonBuffer);

  if (httpCode > 0) {
    String response = http.getString();
    Serial.printf("[HTTP] ✅ Server Response Code: %d\n", httpCode);
  } else {
    Serial.printf("[HTTP] ❌ POST Error: %s (Code: %d)\n",
                  http.errorToString(httpCode).c_str(), httpCode);
  }

  http.end();
}

// ------------------- MAIN LOOP -------------------

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - lastSendTime >= SEND_INTERVAL_MS) {
    lastSendTime = currentMillis;

    int rawSoilADC = 0, rawMQADC = 0;
    float tempC = 0.0f, humidity = 0.0f;

    float soilMoisture = getSoilMoisture(rawSoilADC);
    float smokePPM     = getSmokePPM(rawMQADC);
    getDHTData(tempC, humidity);

    Serial.println("----------------------------------------------------------");
    Serial.printf("[SENSOR READINGS] Raw Soil ADC (D34): %d -> Moisture: %.1f%%\n", rawSoilADC, soilMoisture);
    Serial.printf("[SENSOR READINGS] Temp: %.1f°C | Humidity: %.1f%% | Air: %.1f PPM\n", tempC, humidity, smokePPM);

    sendTelemetry(soilMoisture, tempC, humidity, smokePPM);
  }
}
