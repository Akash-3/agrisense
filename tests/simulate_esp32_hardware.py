import time
import json
import urllib.request
import urllib.error
import random

SERVER_URL = "http://adapters-allows-publicity-sagem.trycloudflare.com/api/v1/telemetry/ingest"
DEVICE_ID = "ESP32_VIRTUAL_HARDWARE_SIMULATOR"

def run_esp32_simulation(iterations=5, delay_sec=2):
    print("============================================================")
    print("   AGRISENSE VIRTUAL ESP32 HARDWARE SIMULATOR CLIENT       ")
    print("============================================================")
    print(f"Target Endpoint : {SERVER_URL}")
    print(f"Device ID       : {DEVICE_ID}")
    print(f"Iterations      : {iterations}")
    print("============================================================\n")

    success_count = 0
    fail_count = 0

    for i in range(1, iterations + 1):
        soil_moisture = round(random.uniform(35.0, 55.0), 1)
        temperature = round(random.uniform(22.0, 31.0), 1)
        humidity = round(random.uniform(55.0, 75.0), 1)
        smoke_ppm = round(random.uniform(60.0, 120.0), 1)

        payload = {
            "device_id": DEVICE_ID,
            "soil_moisture": soil_moisture,
            "soil_status": "ONLINE",
            "temperature": temperature,
            "humidity": humidity,
            "dht_status": "ONLINE",
            "smoke_ppm": smoke_ppm,
            "mq135_status": "ONLINE"
        }

        json_data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ESP32-AgriSense-Virtual-Hardware",
            "Connection": "close"
        }

        req = urllib.request.Request(SERVER_URL, data=json_data, headers=headers)
        
        try:
            start_time = time.time()
            res = urllib.request.urlopen(req, timeout=15)
            elapsed_ms = round((time.time() - start_time) * 1000, 1)
            resp_body = res.read().decode('utf-8')
            resp_json = json.loads(resp_body)

            print(f"[{i}/{iterations}] [OK] HTTP {res.status} ({elapsed_ms}ms) | Soil: {soil_moisture}% | Temp: {temperature}C | Hum: {humidity}% | Smoke: {smoke_ppm}PPM")
            print(f"      Server Response: {resp_json.get('message')}")
            success_count += 1
        except urllib.error.HTTPError as e:
            print(f"[{i}/{iterations}] [FAIL] HTTP ERROR {e.code}: {e.reason}")
            fail_count += 1
        except Exception as e:
            print(f"[{i}/{iterations}] [FAIL] CONNECTION REFUSED / TIMEOUT: {e}")
            fail_count += 1

        if i < iterations:
            time.sleep(delay_sec)

    print("\n============================================================")
    print(f"SIMULATION COMPLETE: {success_count}/{iterations} PASSED (Failures: {fail_count})")
    print("============================================================")

if __name__ == "__main__":
    run_esp32_simulation(iterations=5, delay_sec=2)
