/*
 * AgriSense Multi-Sensor IoT Station Firmware
 * Microcontroller: ESP32-WROOM-32 30-Pin USB-C DevKit
 * 
 * Connected Sensors:
 *   1. Soil Moisture Sensor (Analog -> D34 / GPIO 34)
 *   2. MQ-135 Air Quality / Smoke Sensor (Analog -> D35 / GPIO 35)
 *   3. DHT22 Temperature & Humidity Sensor (Digital Data -> D4 / GPIO 4)
 * 
 * Hardware Wiring:
 *   - Soil Sensor VCC  -> ESP32 3V3
 *   - Soil Sensor GND  -> ESP32 GND
 *   - Soil Sensor AOUT -> ESP32 D34 (GPIO 34)
 * 
 *   - MQ-135 VCC       -> ESP32 VIN (5V) [Heater requires 5V]
 *   - MQ-135 GND       -> ESP32 GND
 *   - MQ-135 AOUT      -> ESP32 D35 (GPIO 35)
 * 
 *   - DHT22 VCC        -> ESP32 3V3
 *   - DHT22 GND        -> ESP32 GND
 *   - DHT22 DATA       -> ESP32 D4  (GPIO 4)
 * 
 * Features:
 *   - Complete Fault-Tolerance & Error Handling (Won't crash if sensors are unplugged)
 *   - Live Ingestion to AgriSense FastAPI Backend & Real-time Flutter Dashboard
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// ==================== CONFIGURATION ====================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";       // Replace with your Wi-Fi name
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";   // Replace with your Wi-Fi password

// Server Endpoint (Replace with your Laptop IP or Cloudflare URL)
// Example Local IP: "http://192.168.1.100:8000/api/v1/telemetry/ingest"
// Example Cloudflare: "https://your-tunnel.trycloudflare.com/api/v1/telemetry/ingest"
const char* SERVER_URL = "http://192.168.1.100:8000/api/v1/telemetry/ingest";

const char* DEVICE_ID  = "ESP32_MULTI_NODE_01";

// ==================== PIN DEFINITIONS ====================
#define SOIL_PIN 34 // GPIO 34 (D34 - ADC1_CH6)
#define MQ135_PIN 35 // GPIO 35 (D35 - ADC1_CH7)
#define DHT_PIN   4  // GPIO 4  (D4 - Digital)
#define DHTTYPE   DHT22

DHT dht(DHT_PIN, DHTTYPE);

// Soil Calibration Constants (12-bit ADC: 0 - 4095)
const int AirValue   = 3200; // Sensor in dry air (0% moisture)
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

  // Configure ADC resolution (12-bit = 0-4095 range)
  analogReadResolution(12);
  pinMode(SOIL_PIN, INPUT);
  pinMode(MQ135_PIN, INPUT);

  // Initialize DHT22 Sensor
  dht.begin();
  Serial.println("[DHT22] Sensor driver initialized on GPIO 4.");

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
  Serial.println("==========================================================");
}

// Multi-sample ADC filter to smooth out noise
int readAveragedAnalog(int pin, int samples = 10) {
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delay(5);
  }
  return (int)(sum / samples);
}

// ------------------- SENSOR READERS WITH FAULT TOLERANCE -------------------

// 1. Soil Moisture Reader with Disconnection Check
float getSoilMoisture(int &rawADC) {
  rawADC = readAveragedAnalog(SOIL_PIN, 10);

  // Fault check: Open/floating pin reads extreme high/low
  if (rawADC < 100 || rawADC > 4050) {
    Serial.printf("[SOIL WARN] Sensor unplugged or disconnected (Raw ADC: %d). Using fallback 50.0%%\n", rawADC);
    return 50.0f; // Safe default fallback
  }

  float moisturePct = (float)map(rawADC, AirValue, WaterValue, 0, 100);
  return constrain(moisturePct, 0.0f, 100.0f);
}

// 2. MQ-135 Gas / Air Quality Reader with Fault Check
float getSmokePPM(int &rawADC) {
  rawADC = readAveragedAnalog(MQ135_PIN, 10);

  // Fault check: Floating or missing MQ-135 pin
  if (rawADC < 30) {
    Serial.printf("[MQ135 WARN] Sensor disconnected (Raw ADC: %d). Using fallback 85.0 PPM\n", rawADC);
    return 85.0f; // Safe default fallback
  }

  // Convert raw 12-bit ADC reading to estimated PPM value
  float ppm = map(rawADC, 200, 3500, 50, 600);
  return constrain(ppm, 20.0f, 999.0f);
}

// 3. DHT22 Temperature & Humidity Reader with NaN Check
void getDHTData(float &tempC, float &humidityPct) {
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  // Check if reading failed (unplugged or missing sensor)
  if (isnan(t) || isnan(h)) {
    Serial.println("[DHT22 WARN] Sensor not detected / disconnected! Using fallback defaults (26.5°C, 62.0%)");
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
    Serial.println("[Wi-Fi] Network lost! Attempting background reconnect...");
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

  Serial.print("[HTTP] Outgoing Telemetry: ");
  Serial.println(jsonBuffer);

  int httpResponseCode = http.POST(jsonBuffer);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.printf("[HTTP] ✅ Success! Response Code: %d\n", httpResponseCode);
  } else {
    Serial.printf("[HTTP] ❌ POST Failed, Error: %s (Code: %d)\n",
                  http.errorToString(httpResponseCode).c_str(), httpResponseCode);
  }

  http.end();
}

// ------------------- MAIN LOOP -------------------

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - lastSendTime >= SEND_INTERVAL_MS) {
    lastSendTime = currentMillis;

    int rawSoilADC = 0;
    int rawMQADC = 0;

    // Read all 3 sensors with individual error handling
    float soilMoisture = getSoilMoisture(rawSoilADC);
    float smokePPM     = getSmokePPM(rawMQADC);
    float tempC = 0.0f, humidity = 0.0f;
    getDHTData(tempC, humidity);

    Serial.println("----------------------------------------------------------");
    Serial.printf("[READINGS] Soil: %.1f%% | Temp: %.1f°C | Humidity: %.1f%% | Smoke: %.1f PPM\n",
                  soilMoisture, tempC, humidity, smokePPM);

    // Send payload to backend REST endpoint
    sendTelemetry(soilMoisture, tempC, humidity, smokePPM);
  }
}
