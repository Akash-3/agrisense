/*
 * ============================================================
 * AgriSense ESP32 Multi-Sensor IoT Station
 * ============================================================
 *
 * Hardware:
 *   Soil Moisture Sensor
 *     VCC  -> ESP32 3V3
 *     GND  -> ESP32 GND
 *     AOUT -> GPIO 34
 *
 *   MQ-135
 *     VCC  -> ESP32 VIN (5V)
 *     GND  -> ESP32 GND
 *     AOUT -> GPIO 35
 *
 *   DHT22
 *     VCC  -> ESP32 3V3
 *     GND  -> ESP32 GND
 *     DATA -> GPIO 4
 *
 * Network:
 *   ESP32 -> Internet -> Tailscale Funnel -> FastAPI
 *
 * Public backend:
 *   https://admin.tail4fe027.ts.net
 *
 * Telemetry endpoint:
 *   https://admin.tail4fe027.ts.net/api/v1/telemetry/ingest
 *
 * Features:
 *   - HTTPS telemetry transmission
 *   - Wi-Fi auto-reconnection
 *   - DNS resolution diagnostics
 *   - HTTPS/TLS diagnostics
 *   - HTTP status diagnostics
 *   - Sensor disconnection detection
 *   - Explicit null values for disconnected sensors
 *   - No fake sensor fallbacks
 *   - 5-second telemetry interval
 *
 * NOTE:
 *   client.setInsecure() is intentionally used during development.
 *   This disables TLS certificate validation.
 *   Proper certificate validation should be added before production.
 * ============================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <DHT.h>

// ============================================================
// CONFIGURATION
// ============================================================

// Wi-Fi credentials
const char* WIFI_SSID     = "Hiii";
const char* WIFI_PASSWORD = "kavya432";

// Public AgriSense backend through Tailscale Funnel
const char* SERVER_URL =
    "https://admin.tail4fe027.ts.net/api/v1/telemetry/ingest";

const char* DEVICE_ID = "ESP32_MULTI_NODE_01";

// ============================================================
// PIN DEFINITIONS
// ============================================================

#define SOIL_PIN  34
#define MQ135_PIN 35
#define DHT_PIN   4
#define DHTTYPE   DHT22

DHT dht(DHT_PIN, DHTTYPE);

// ============================================================
// SOIL MOISTURE CALIBRATION
// ============================================================
//
// Dry air      = 0%
// Water        = 100%
//

const int AirValue   = 4095;
const int WaterValue = 2650;

// ============================================================
// TIMING
// ============================================================

const unsigned long SEND_INTERVAL_MS = 5000;

unsigned long lastSendTime = 0;

// ============================================================
// NETWORK CONFIGURATION
// ============================================================

const unsigned long WIFI_CONNECT_TIMEOUT_MS = 20000;
const unsigned long WIFI_RECONNECT_TIMEOUT_MS = 10000;

const unsigned long HTTPS_TIMEOUT_MS = 20000;
const unsigned long TLS_HANDSHAKE_TIMEOUT_SECONDS = 15;

// ============================================================
// WIFI CONNECTION
// ============================================================

bool connectToWiFi(unsigned long timeoutMs) {

  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  Serial.println();
  Serial.println("[Wi-Fi] Connecting...");

  WiFi.mode(WIFI_STA);

  // Automatically reconnect if the access point disappears.
  WiFi.setAutoReconnect(true);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startTime = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - startTime < timeoutMs) {

    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {

    Serial.println("[Wi-Fi] ❌ Connection failed.");

    Serial.print("[Wi-Fi] Status code: ");
    Serial.println(WiFi.status());

    return false;
  }

  Serial.println("[Wi-Fi] ✅ Connected successfully.");

  Serial.print("[Wi-Fi] IP address: ");
  Serial.println(WiFi.localIP());

  Serial.print("[Wi-Fi] Gateway: ");
  Serial.println(WiFi.gatewayIP());

  Serial.print("[Wi-Fi] Subnet: ");
  Serial.println(WiFi.subnetMask());

  Serial.print("[Wi-Fi] DNS: ");
  Serial.println(WiFi.dnsIP());

  Serial.print("[Wi-Fi] RSSI: ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");

  return true;
}

// ============================================================
// WIFI RECONNECTION
// ============================================================

bool ensureWiFiConnection() {

  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  Serial.println();
  Serial.println("[Wi-Fi] ⚠️ Connection lost.");
  Serial.println("[Wi-Fi] Attempting reconnection...");

  WiFi.disconnect();

  delay(500);

  return connectToWiFi(WIFI_RECONNECT_TIMEOUT_MS);
}

// ============================================================
// ANALOG SENSOR READING
// ============================================================

int readAveragedAnalog(int pin, int samples = 10) {

  long sum = 0;

  for (int i = 0; i < samples; i++) {

    sum += analogRead(pin);

    delay(5);
  }

  return (int)(sum / samples);
}

// ============================================================
// SOIL MOISTURE SENSOR
// ============================================================

bool getSoilMoisture(float &moisturePct, int &rawADC) {

  rawADC = readAveragedAnalog(SOIL_PIN, 10);

  // Basic electrical fault detection.
  if (rawADC < 10) {

    Serial.printf(
        "[SOIL FAULT] Sensor disconnected or shorted "
        "(Raw ADC: %d)\n",
        rawADC
    );

    return false;
  }

  moisturePct =
      (float)map(
          rawADC,
          AirValue,
          WaterValue,
          0,
          100
      );

  moisturePct =
      constrain(
          moisturePct,
          0.0f,
          100.0f
      );

  return true;
}

// ============================================================
// MQ-135 SENSOR
// ============================================================

bool getSmokePPM(float &smokePPM, int &rawADC) {

  rawADC = readAveragedAnalog(MQ135_PIN, 10);

  // Basic electrical fault detection.
  if (rawADC < 10) {

    Serial.printf(
        "[MQ135 FAULT] Sensor disconnected "
        "(Raw ADC: %d)\n",
        rawADC
    );

    return false;
  }

  /*
   * Existing project mapping retained.
   *
   * IMPORTANT:
   * This is an application-level ADC-to-PPM mapping,
   * not laboratory-calibrated gas concentration measurement.
   */

  smokePPM =
      (float)map(
          rawADC,
          200,
          3500,
          50,
          600
      );

  smokePPM =
      constrain(
          smokePPM,
          20.0f,
          999.0f
      );

  return true;
}

// ============================================================
// DHT22 SENSOR
// ============================================================

bool getDHTData(float &tempC, float &humidityPct) {

  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (isnan(t) || isnan(h)) {

    Serial.println(
        "[DHT22 FAULT] Sensor disconnected "
        "or invalid NaN reading."
    );

    return false;
  }

  tempC = t;
  humidityPct = h;

  return true;
}

// ============================================================
// DNS DIAGNOSTIC
// ============================================================

bool checkBackendDNS() {

  Serial.println("[DNS] Resolving backend hostname...");

  IPAddress resolvedIP;

  if (!WiFi.hostByName(
          "admin.tail4fe027.ts.net",
          resolvedIP
      )) {

    Serial.println(
        "[DNS] ❌ Failed to resolve "
        "admin.tail4fe027.ts.net"
    );

    return false;
  }

  Serial.print("[DNS] ✅ Resolved to: ");
  Serial.println(resolvedIP);

  return true;
}

// ============================================================
// HTTPS TELEMETRY TRANSMISSION
// ============================================================

void sendTelemetry(
    bool soilOk,
    float soilMoisture,
    bool dhtOk,
    float tempC,
    float humidity,
    bool mqOk,
    float smokePPM
) {

  // ----------------------------------------------------------
  // WIFI CHECK
  // ----------------------------------------------------------

  if (!ensureWiFiConnection()) {

    Serial.println(
        "[HTTP WAN] ❌ No Wi-Fi connection. "
        "Telemetry skipped."
    );

    return;
  }

  // ----------------------------------------------------------
  // JSON VALUES
  // ----------------------------------------------------------

  String soilStr =
      soilOk
          ? String(soilMoisture, 1)
          : "null";

  String tempStr =
      dhtOk
          ? String(tempC, 1)
          : "null";

  String humStr =
      dhtOk
          ? String(humidity, 1)
          : "null";

  String smokeStr =
      mqOk
          ? String(smokePPM, 1)
          : "null";

  String soilStatus =
      soilOk
          ? "ONLINE"
          : "SENSOR_DISCONNECTED";

  String dhtStatus =
      dhtOk
          ? "ONLINE"
          : "SENSOR_DISCONNECTED";

  String mqStatus =
      mqOk
          ? "ONLINE"
          : "SENSOR_DISCONNECTED";

  // ----------------------------------------------------------
  // JSON PAYLOAD
  // ----------------------------------------------------------

  String jsonPayload = "{";

  jsonPayload +=
      "\"device_id\":\"" +
      String(DEVICE_ID) +
      "\",";

  jsonPayload +=
      "\"soil_moisture\":" +
      soilStr +
      ",";

  jsonPayload +=
      "\"soil_status\":\"" +
      soilStatus +
      "\",";

  jsonPayload +=
      "\"temperature\":" +
      tempStr +
      ",";

  jsonPayload +=
      "\"humidity\":" +
      humStr +
      ",";

  jsonPayload +=
      "\"dht_status\":\"" +
      dhtStatus +
      "\",";

  jsonPayload +=
      "\"smoke_ppm\":" +
      smokeStr +
      ",";

  jsonPayload +=
      "\"mq135_status\":\"" +
      mqStatus +
      "\"";

  jsonPayload += "}";

  // ----------------------------------------------------------
  // LOG
  // ----------------------------------------------------------

  Serial.println();
  Serial.println("----------------------------------------------------------");

  Serial.println(
      "[HTTP WAN] Preparing HTTPS telemetry transmission..."
  );

  Serial.print("[HTTP WAN] Target: ");
  Serial.println(SERVER_URL);

  Serial.print("[HTTP WAN] Payload: ");
  Serial.println(jsonPayload);

  // ----------------------------------------------------------
  // DNS TEST
  // ----------------------------------------------------------

  if (!checkBackendDNS()) {

    Serial.println(
        "[HTTP WAN] ❌ DNS resolution failed. "
        "POST aborted."
    );

    return;
  }

  // ----------------------------------------------------------
  // SECURE CLIENT
  // ----------------------------------------------------------

  WiFiClientSecure client;

  /*
   * Development mode:
   * Do not validate the remote TLS certificate.
   *
   * This avoids certificate provisioning being a
   * variable during initial Funnel integration testing.
   *
   * TODO for production:
   * Replace setInsecure() with proper certificate
   * validation / CA certificate.
   */

  client.setInsecure();

  client.setHandshakeTimeout(
      TLS_HANDSHAKE_TIMEOUT_SECONDS
  );

  // ----------------------------------------------------------
  // HTTP CLIENT
  // ----------------------------------------------------------

  HTTPClient http;

  http.setTimeout(HTTPS_TIMEOUT_MS);

  /*
   * Disable keep-alive connection reuse.
   *
   * This is intentional for the current ESP32
   * telemetry reliability configuration.
   */

  http.setReuse(false);

  http.addHeader(
      "Content-Type",
      "application/json"
  );

  http.addHeader(
      "User-Agent",
      "ESP32-AgriSense-Node"
  );

  http.addHeader(
      "Connection",
      "close"
  );

  // ----------------------------------------------------------
  // BEGIN HTTPS
  // ----------------------------------------------------------

  Serial.println(
      "[HTTPS] Initializing secure connection..."
  );

  if (!http.begin(client, SERVER_URL)) {

    Serial.println(
        "[HTTPS] ❌ Failed to initialize HTTPS client."
    );

    return;
  }

  Serial.println(
      "[HTTPS] ✅ HTTPS client initialized."
  );

  // ----------------------------------------------------------
  // POST
  // ----------------------------------------------------------

  Serial.println(
      "[HTTP WAN] Sending telemetry POST..."
  );

  int httpCode =
      http.POST(jsonPayload);

  // ----------------------------------------------------------
  // SUCCESS / SERVER RESPONSE
  // ----------------------------------------------------------

  if (httpCode > 0) {

    Serial.printf(
        "[HTTP WAN] Server response code: %d\n",
        httpCode
    );

    String response =
        http.getString();

    Serial.print(
        "[HTTP WAN] Server response: "
    );

    Serial.println(response);

    if (httpCode >= 200 &&
        httpCode < 300) {

      Serial.println(
          "[HTTP WAN] ✅ Telemetry successfully delivered."
      );

    } else {

      Serial.println(
          "[HTTP WAN] ⚠️ Server returned "
          "a non-success HTTP status."
      );
    }

  }

  // ----------------------------------------------------------
  // CONNECTION ERROR
  // ----------------------------------------------------------

  else {

    Serial.printf(
        "[HTTP WAN] ❌ POST failed. "
        "HTTP error code: %d\n",
        httpCode
    );

    Serial.print(
        "[HTTP WAN] Error description: "
    );

    Serial.println(
        http.errorToString(httpCode)
    );

    Serial.print(
        "[HTTP WAN] Wi-Fi status: "
    );

    Serial.println(
        WiFi.status()
    );

    Serial.print(
        "[HTTP WAN] ESP32 IP: "
    );

    Serial.println(
        WiFi.localIP()
    );

    Serial.print(
        "[HTTP WAN] DNS server: "
    );

    Serial.println(
        WiFi.dnsIP()
    );

    Serial.print(
        "[HTTP WAN] RSSI: "
    );

    Serial.print(
        WiFi.RSSI()
    );

    Serial.println(" dBm");
  }

  // ----------------------------------------------------------
  // CLEANUP
  // ----------------------------------------------------------

  http.end();

  Serial.println(
      "[HTTPS] Connection closed."
  );
}

// ============================================================
// SETUP
// ============================================================

void setup() {

  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println(
      "=========================================================="
  );

  Serial.println(
      "     AgriSense ESP32 Multi-Sensor IoT Station"
  );

  Serial.println(
      "=========================================================="
  );

  Serial.println();

  // ----------------------------------------------------------
  // HARDWARE INITIALIZATION
  // ----------------------------------------------------------

  analogReadResolution(12);

  pinMode(
      SOIL_PIN,
      INPUT
  );

  pinMode(
      MQ135_PIN,
      INPUT
  );

  dht.begin();

  Serial.println(
      "[DHT22] Sensor driver initialized on GPIO 4."
  );

  // ----------------------------------------------------------
  // NETWORK INFORMATION
  // ----------------------------------------------------------

  Serial.println();
  Serial.println(
      "[Network] Public backend:"
  );

  Serial.println(
      "https://admin.tail4fe027.ts.net"
  );

  Serial.println();

  // ----------------------------------------------------------
  // WIFI
  // ----------------------------------------------------------

  Serial.print(
      "[Wi-Fi] Connecting to network: "
  );

  Serial.println(
      WIFI_SSID
  );

  if (!connectToWiFi(
          WIFI_CONNECT_TIMEOUT_MS
      )) {

    Serial.println();
    Serial.println(
        "[Wi-Fi] ❌ Initial Wi-Fi connection failed."
    );

    Serial.println(
        "[System] Restarting ESP32 in 5 seconds..."
    );

    delay(5000);

    ESP.restart();
  }

  Serial.println();
  Serial.println(
      "=========================================================="
  );

  Serial.println(
      "[System] ESP32 initialization complete."
  );

  Serial.println(
      "[System] Telemetry interval: 5 seconds."
  );

  Serial.println(
      "=========================================================="
  );
}

// ============================================================
// MAIN LOOP
// ============================================================

void loop() {

  unsigned long currentMillis =
      millis();

  // ----------------------------------------------------------
  // TELEMETRY INTERVAL
  // ----------------------------------------------------------

  if (
      currentMillis - lastSendTime >=
      SEND_INTERVAL_MS
  ) {

    lastSendTime =
        currentMillis;

    // --------------------------------------------------------
    // SENSOR VARIABLES
    // --------------------------------------------------------

    int rawSoilADC = 0;
    int rawMQADC = 0;

    float soilMoisture = 0.0f;
    float smokePPM = 0.0f;

    float tempC = 0.0f;
    float humidity = 0.0f;

    // --------------------------------------------------------
    // READ SENSORS
    // --------------------------------------------------------

    bool soilOk =
        getSoilMoisture(
            soilMoisture,
            rawSoilADC
        );

    bool mqOk =
        getSmokePPM(
            smokePPM,
            rawMQADC
        );

    bool dhtOk =
        getDHTData(
            tempC,
            humidity
        );

    // --------------------------------------------------------
    // SERIAL SENSOR REPORT
    // --------------------------------------------------------

    Serial.println();
    Serial.println(
        "----------------------------------------------------------"
    );

    if (soilOk) {

      Serial.printf(
          "[READINGS] Soil Moisture: %.1f%% "
          "(ADC %d)\n",
          soilMoisture,
          rawSoilADC
      );

    } else {

      Serial.println(
          "[READINGS] ⚠ Soil Moisture: DISCONNECTED"
      );
    }

    if (dhtOk) {

      Serial.printf(
          "[READINGS] Temperature: %.1f°C | "
          "Humidity: %.1f%%\n",
          tempC,
          humidity
      );

    } else {

      Serial.println(
          "[READINGS] ⚠ DHT22: DISCONNECTED"
      );
    }

    if (mqOk) {

      Serial.printf(
          "[READINGS] Air Quality: %.1f PPM "
          "(ADC %d)\n",
          smokePPM,
          rawMQADC
      );

    } else {

      Serial.println(
          "[READINGS] ⚠ MQ-135: DISCONNECTED"
      );
    }

    // --------------------------------------------------------
    // SEND TO BACKEND
    // --------------------------------------------------------

    sendTelemetry(
        soilOk,
        soilMoisture,
        dhtOk,
        tempC,
        humidity,
        mqOk,
        smokePPM
    );
  }

  // Small yield/delay to keep the ESP32 responsive.
  delay(10);
}