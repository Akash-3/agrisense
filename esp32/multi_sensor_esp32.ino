/*
 * AgriSense ESP32 Multi-Sensor IoT Station Firmware
 * Microcontroller: ESP32-WROOM-32 30-Pin USB-C DevKit
 * 
 * Hardware Connections:
 *   - Soil Moisture Sensor VCC  -> ESP32 3V3
 *   - Soil Moisture Sensor GND  -> ESP32 GND
 *   - Soil Moisture Sensor AOUT -> ESP32 D34 (GPIO 34)
 * 
 *   - MQ-135 Air Sensor VCC     -> ESP32 VIN (5V)
 *   - MQ-135 Air Sensor GND     -> ESP32 GND
 *   - MQ-135 Air Sensor AOUT    -> ESP32 D35 (GPIO 35)
 * 
 *   - DHT22 Temp Sensor VCC     -> ESP32 3V3
 *   - DHT22 Temp Sensor GND     -> ESP32 GND
 *   - DHT22 Temp Sensor DATA    -> ESP32 D4  (GPIO 4)
 * 
 * Status Reporting:
 *   - Real Hardware Disconnection Detection (NO Fake Fallbacks)
 *   - Sends null and status="SENSOR_DISCONNECTED" to dashboard when unplugged!
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// ==================== CONFIGURATION ====================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";       // Replace with your Wi-Fi name
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";   // Replace with your Wi-Fi password

// Server Endpoint (Tailscale Tailnet IP: 100.126.23.88 or Local Wi-Fi IP: 172.19.17.125)
const char* SERVER_URL = "http://100.126.23.88:8000/api/v1/telemetry/ingest";
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

// ------------------- SENSOR READERS WITH NO FAKE FALLBACKS -------------------

// 1. Soil Moisture Reader
bool getSoilMoisture(float &moisturePct, int &rawADC) {
  rawADC = readAveragedAnalog(SOIL_PIN, 10);

  // Disconnection check: 0 indicates shorted/unconnected pin
  if (rawADC < 10) {
    Serial.printf("[SOIL FAULT] ⚠️ Sensor disconnected or shorted (Raw ADC: %d)\n", rawADC);
    return false; // Disconnected
  }

  moisturePct = (float)map(rawADC, AirValue, WaterValue, 0, 100);
  moisturePct = constrain(moisturePct, 0.0f, 100.0f);
  return true; // Online
}

// 2. MQ-135 Gas Reader
bool getSmokePPM(float &smokePPM, int &rawADC) {
  rawADC = readAveragedAnalog(MQ135_PIN, 10);

  if (rawADC < 10) {
    Serial.printf("[MQ135 FAULT] ⚠️ Sensor unplugged (Raw ADC: %d)\n", rawADC);
    return false; // Disconnected
  }

  smokePPM = (float)map(rawADC, 200, 3500, 50, 600);
  smokePPM = constrain(smokePPM, 20.0f, 999.0f);
  return true; // Online
}

// 3. DHT22 Temp & Humidity Reader
bool getDHTData(float &tempC, float &humidityPct) {
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (isnan(t) || isnan(h)) {
    Serial.println("[DHT22 FAULT] ⚠️ Sensor disconnected / NaN reading!");
    return false; // Disconnected
  }

  tempC = t;
  humidityPct = h;
  return true; // Online
}

// ------------------- HTTP TELEMETRY TRANSMITTER -------------------

void sendTelemetry(bool soilOk, float soilMoisture,
                   bool dhtOk, float tempC, float humidity,
                   bool mqOk, float smokePPM) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[Wi-Fi] Network connection lost! Reconnecting...");
    WiFi.reconnect();
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  // Format JSON payload with explicit nulls and status indicators
  String soilStr   = soilOk ? String(soilMoisture, 1) : "null";
  String tempStr   = dhtOk  ? String(tempC, 1)        : "null";
  String humStr    = dhtOk  ? String(humidity, 1)     : "null";
  String smokeStr  = mqOk   ? String(smokePPM, 1)     : "null";

  String soilStatus = soilOk ? "ONLINE" : "SENSOR_DISCONNECTED";
  String dhtStatus  = dhtOk  ? "ONLINE" : "SENSOR_DISCONNECTED";
  String mqStatus   = mqOk   ? "ONLINE" : "SENSOR_DISCONNECTED";

  String jsonPayload = "{";
  jsonPayload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  jsonPayload += "\"soil_moisture\":" + soilStr + ",";
  jsonPayload += "\"soil_status\":\"" + soilStatus + "\",";
  jsonPayload += "\"temperature\":" + tempStr + ",";
  jsonPayload += "\"humidity\":" + humStr + ",";
  jsonPayload += "\"dht_status\":\"" + dhtStatus + "\",";
  jsonPayload += "\"smoke_ppm\":" + smokeStr + ",";
  jsonPayload += "\"mq135_status\":\"" + mqStatus + "\"";
  jsonPayload += "}";

  Serial.print("[HTTP] Dispatching Telemetry: ");
  Serial.println(jsonPayload);

  int httpCode = http.POST(jsonPayload);

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
    float soilMoisture = 0.0f, smokePPM = 0.0f;
    float tempC = 0.0f, humidity = 0.0f;

    bool soilOk = getSoilMoisture(soilMoisture, rawSoilADC);
    bool mqOk   = getSmokePPM(smokePPM, rawMQADC);
    bool dhtOk  = getDHTData(tempC, humidity);

    Serial.println("----------------------------------------------------------");
    if (soilOk) Serial.printf("[READINGS] Soil Moisture: %.1f%% (ADC %d)\n", soilMoisture, rawSoilADC);
    else        Serial.println("[READINGS] ⚠️ Soil Moisture Sensor: DISCONNECTED");

    if (dhtOk)  Serial.printf("[READINGS] Temp: %.1f°C | Humidity: %.1f%%\n", tempC, humidity);
    else        Serial.println("[READINGS] ⚠️ DHT22 Sensor: DISCONNECTED");

    if (mqOk)   Serial.printf("[READINGS] Air Quality: %.1f PPM (ADC %d)\n", smokePPM, rawMQADC);
    else        Serial.println("[READINGS] ⚠️ MQ-135 Sensor: DISCONNECTED");

    sendTelemetry(soilOk, soilMoisture, dhtOk, tempC, humidity, mqOk, smokePPM);
  }
}
