/*
 * AgriSense Aerial Drone Node Firmware
 * Microcontroller: ESP32 DevKit V1
 * Sensors: 
 *   - Adafruit AS7341 10-Channel Spectral Sensor (I2C: SDA=21, SCL=22)
 *   - DHT22 Temperature & Humidity Sensor (Data Pin=GPIO 4)
 *   - MQ-2 Smoke & Combustible Gas Sensor (Analog Pin=GPIO 34)
 * Communication: Wi-Fi HTTP POST (JSON Payload to FastAPI Backend)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_AS7341.h>
#include <DHT.h>
#include <ArduinoJson.h>

// --- Configuration ---
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL = "http://192.168.1.100:8000/api/v1/sensors"; // Replace with your server IP

// Sensor Pin Definitions
#define DHTPIN 4
#define DHTTYPE DHT22
#define MQ2_ANALOG_PIN 34

// Objects
DHT dht(DHTPIN, DHTTYPE);
Adafruit_AS7341 as7341;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[AgriSense] Initializing Aerial Drone Node...");

  // Initialize Sensors
  dht.begin();
  
  if (!as7341.begin()) {
    Serial.println("[Error] Could not find Adafruit AS7341 sensor! Check I2C wiring.");
  } else {
    Serial.println("[Success] AS7341 Spectral Sensor Initialized.");
    as7341.setATIME(100);
    as7341.setASTEP(999);
    as7341.setGain(AS7341_GAIN_256X);
  }

  // Connect Wi-Fi
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
    // 1. Read DHT22
    float temp = dht.readTemperature();
    float hum = dht.readHumidity();

    // 2. Read MQ-2
    int mq2Raw = analogRead(MQ2_ANALOG_PIN);

    // 3. Read AS7341 Spectral Channels
    uint16_t readings[12];
    bool spectralSuccess = as7341.readAllChannels(readings);

    // Build JSON Document
    StaticJsonDocument<512> doc;
    doc["device_id"] = "drone01";
    doc["device_type"] = "drone";
    
    if (!isnan(temp)) doc["temperature"] = temp;
    if (!isnan(hum)) doc["humidity"] = hum;
    doc["mq2_raw"] = mq2Raw;

    if (spectralSuccess) {
      JsonObject spectral = doc.createNestedObject("spectral");
      spectral["ch415nm"] = as7341.getChannel(AS7341_CHANNEL_415nm);
      spectral["ch445nm"] = as7341.getChannel(AS7341_CHANNEL_445nm);
      spectral["ch480nm"] = as7341.getChannel(AS7341_CHANNEL_480nm);
      spectral["ch515nm"] = as7341.getChannel(AS7341_CHANNEL_515nm);
      spectral["ch555nm"] = as7341.getChannel(AS7341_CHANNEL_555nm);
      spectral["ch590nm"] = as7341.getChannel(AS7341_CHANNEL_590nm);
      spectral["ch630nm"] = as7341.getChannel(AS7341_CHANNEL_630nm);
      spectral["ch680nm"] = as7341.getChannel(AS7341_CHANNEL_680nm);
      spectral["clear"]   = as7341.getChannel(AS7341_CHANNEL_CLEAR);
      spectral["nir"]     = as7341.getChannel(AS7341_CHANNEL_NIR);
    }

    String jsonPayload;
    serializeJson(doc, jsonPayload);

    // Send HTTP POST
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.POST(jsonPayload);
    if (httpResponseCode > 0) {
      Serial.printf("[HTTP] POST Response code: %d\n", httpResponseCode);
    } else {
      Serial.printf("[HTTP] POST failed, error: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  } else {
    Serial.println("[Wi-Fi] Disconnected! Reconnecting...");
    WiFi.reconnect();
  }

  // Sample every 5 seconds
  delay(5000);
}
