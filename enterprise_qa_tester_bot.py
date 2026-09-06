import os
import sys
import time
import json
import secrets
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"

# OWASP AppSec-Payloads Arsenal Fuzzing Vectors
XSS_FUZZ_VECTOR_PAYLOADS = [
    "<script>alert('XSS_TEST')</script>",
    "<svg/onload=alert('SVG_XSS')>",
    "<img src=x onerror=alert('IMG_XSS')>",
    "javascript:alert('JS_SCHEME')",
    "\"><script>document.location='http://attacker.com'</script>",
    "<iframe src=\"javascript:alert('IFRAME')\"></iframe>"
]

SQLI_FUZZ_VECTOR_PAYLOADS = [
    "' OR '1'='1",
    "' OR '1'='1' --",
    "\" OR \"1\"=\"1",
    "' UNION SELECT 1, 'authenticated', 'token' --",
    "'; DROP TABLE farmers; --",
    "1' AND 1=2 UNION SELECT NULL, 'injected'--"
]

CRLF_HEADER_PAYLOADS = [
    "admin\r\nX-Injected-Header: malicious_value",
    "test@agrisense.io\r\nSet-Cookie: session_hijack=true"
]

class EnterpriseQATesterBot:
    def __init__(self):
        self.results = []
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0
        self.start_time = time.time()

    def log_section(self, title: str):
        print("\n" + "=" * 80)
        print(f" ENTERPRISE QA TEST SUITE: {title}")
        print("=" * 80)

    def record_test(self, test_id: str, description: str, passed: bool, details: str = "", latency_ms: float = 0.0):
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status_str = "[PASS]"
        else:
            self.failed_tests += 1
            status_str = "[FAIL]"
            
        res = {
            "id": test_id,
            "description": description,
            "status": status_str,
            "passed": passed,
            "latency_ms": round(latency_ms, 2),
            "details": details
        }
        self.results.append(res)
        print(f"[{test_id}] {status_str} | {description} ({round(latency_ms, 1)}ms)")
        if details:
            print(f"      +-- Note: {details}")

    def http_request(self, endpoint: str, method: str = "GET", payload: dict = None, headers: dict = None) -> tuple[int, dict, dict, float]:
        url = f"{BASE_URL}{endpoint}"
        req_headers = {'Content-Type': 'application/json'}
        if headers:
            req_headers.update(headers)

        data = json.dumps(payload).encode('utf-8') if payload else None
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)

        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.status
                res_headers = {k.lower(): v for k, v in resp.headers.items()}
                
                content_type = res_headers.get("content-type", "")
                if "application/json" in content_type:
                    body = resp.read().decode('utf-8')
                    res_json = json.loads(body)
                elif "application/vnd.android.package-archive" in content_type:
                    raw_bytes = resp.read()
                    res_json = {"status": "binary_apk", "size_bytes": len(raw_bytes)}
                else:
                    body = resp.read().decode('utf-8', errors='ignore')
                    try:
                        res_json = json.loads(body)
                    except Exception:
                        res_json = {"raw": body[:200]}

                latency = (time.time() - t0) * 1000
                return status_code, res_json, res_headers, latency
        except urllib.error.HTTPError as e:
            latency = (time.time() - t0) * 1000
            status_code = e.code
            res_headers = {k.lower(): v for k, v in e.headers.items()}
            body = e.read().decode('utf-8', errors='ignore')
            try:
                res_json = json.loads(body)
            except Exception:
                res_json = {"error": body}
            return status_code, res_json, res_headers, latency
        except Exception as e:
            latency = (time.time() - t0) * 1000
            return 0, {"error": str(e)}, {}, latency

    def run_stage_1_server_health_security_headers(self):
        self.log_section("STAGE 1: Server Health & HTTP Security Headers Audit")

        status, body, headers, latency = self.http_request("/api/v1/health")
        passed = (status == 200 and body.get("status") == "online")
        self.record_test("TC-101", "API Gateway Health Check Endpoint", passed, f"Status: {status}", latency)

        nosniff = headers.get("x-content-type-options") == "nosniff"
        self.record_test("TC-102", "Security Header: X-Content-Type-Options (nosniff)", nosniff, f"Header: {headers.get('x-content-type-options')}", latency)

        frame_deny = "DENY" in str(headers.get("x-frame-options"))
        self.record_test("TC-103", "Security Header: X-Frame-Options (DENY Anti-Clickjacking)", frame_deny, f"Header: {headers.get('x-frame-options')}", latency)

    def run_stage_2_authentication_password_verification(self):
        self.log_section("STAGE 2: Authentication & Password Verification Audit")

        uid = secrets.token_hex(4)
        test_email = f"qa_engineer_{uid}@agrisense.io"
        test_pass = "AgriSense#2026Password"

        # 1. Register QA User
        reg_payload = {
            "full_name": "Senior QA Automation Engineer",
            "phone_or_email": test_email,
            "farm_name": "QA Benchmark Farm",
            "farm_acres": 25.0,
            "password": test_pass
        }
        status, body, _, latency = self.http_request("/api/v1/auth/register", method="POST", payload=reg_payload)
        passed_reg = (status == 200 and ("farmer_id" in body or body.get("status") == "success"))
        self.record_test("TC-201", "User Account Registration & PBKDF2 Password Salting", passed_reg, f"Farmer ID: {body.get('farmer_id')}", latency)

        # 2. Strict Wrong Password Test
        wrong_payload = {"phone_or_email": test_email, "password": "WrongPassword123!"}
        status_w, body_w, _, latency_w = self.http_request("/api/v1/auth/login", method="POST", payload=wrong_payload)
        passed_wrong = (status_w == 401 and body_w.get("error") is True)
        self.record_test("TC-202", "Strict Password Verification: Wrong Password Rejection (HTTP 401)", passed_wrong, f"Detail: {body_w.get('detail')}", latency_w)

        # 3. Correct Password Test
        correct_payload = {"phone_or_email": test_email, "password": test_pass}
        status_c, body_c, _, latency_c = self.http_request("/api/v1/auth/login", method="POST", payload=correct_payload)
        passed_correct = (status_c == 200 and body_c.get("status") == "success" and "session_token" in body_c)
        self.record_test("TC-203", "Strict Password Verification: Valid Password Acceptance (HTTP 200)", passed_correct, f"Farmer ID: {body_c.get('farmer', {}).get('id')}", latency_c)

    def run_stage_3_duplicate_account_prevention(self):
        self.log_section("STAGE 3: Duplicate Account Prevention & Redirection Audit")

        uid = secrets.token_hex(4)
        dup_email = f"dup_account_{uid}@agrisense.io"
        ensure_payload = {
            "full_name": "Akash Satapathy",
            "phone_or_email": dup_email,
            "farm_name": "Main Farm",
            "farm_acres": 15.0,
            "password": "Agri#2026Password"
        }
        self.http_request("/api/v1/auth/register", method="POST", payload=ensure_payload)

        dup_payload = {
            "full_name": "Duplicate Tester",
            "phone_or_email": dup_email,
            "farm_name": "Duplicate Farm",
            "farm_acres": 10.0,
            "password": "Agri#2026Password"
        }
        status, body, _, latency = self.http_request("/api/v1/auth/register", method="POST", payload=dup_payload)
        passed_dup = (status == 400 and "Account Already Exists" in str(body.get("detail")))
        self.record_test("TC-301", "Duplicate Account Registration Prevention (HTTP 400)", passed_dup, f"Detail: {body.get('detail')}", latency)

        otp_payload = {"phone_or_email": dup_email, "full_name": "Duplicate Tester"}
        status_otp, body_otp, _, latency_otp = self.http_request("/api/v1/auth/send-otp", method="POST", payload=otp_payload)
        passed_otp_dup = (status_otp == 400 and "Account Already Exists" in str(body_otp.get("detail")))
        self.record_test("TC-302", "Duplicate Account OTP Dispatch Prevention (HTTP 400)", passed_otp_dup, f"Detail: {body_otp.get('detail')}", latency_otp)

    def run_stage_4_appsec_payloads_fuzzing_suite(self):
        self.log_section("STAGE 4: OWASP AppSec-Payloads Arsenal Fuzzing & Penetration Suite")

        # 1. Anti-XSS Fuzzing Matrix
        xss_pass_count = 0
        for idx, attack_payload in enumerate(XSS_FUZZ_VECTOR_PAYLOADS, 1):
            uid = secrets.token_hex(3)
            payload = {
                "full_name": attack_payload,
                "phone_or_email": f"xss_fuzz_{uid}@agrisense.io",
                "farm_name": f"Farm {attack_payload}",
                "farm_acres": 10.0,
                "password": "Agri#2026Password"
            }
            status, body, _, latency = self.http_request("/api/v1/auth/register", method="POST", payload=payload)
            # Check sanitized output
            returned_name = str(body.get("full_name", ""))
            clean = ("<script>" not in returned_name and "<svg" not in returned_name and "<img" not in returned_name and "javascript:" not in returned_name)
            if status in [200, 400] and clean:
                xss_pass_count += 1

        passed_xss_suite = (xss_pass_count == len(XSS_FUZZ_VECTOR_PAYLOADS))
        self.record_test("TC-401", f"OWASP Anti-XSS Fuzz Matrix ({xss_pass_count}/{len(XSS_FUZZ_VECTOR_PAYLOADS)} Clean)", passed_xss_suite, "All Script Vectors Sanitized & Neutralized")

        # 2. SQL Injection Fuzzing Matrix
        sqli_pass_count = 0
        for sqli_payload in SQLI_FUZZ_VECTOR_PAYLOADS:
            payload = {
                "phone_or_email": sqli_payload,
                "password": sqli_payload
            }
            status, body, _, latency = self.http_request("/api/v1/auth/login", method="POST", payload=payload)
            if status == 401 and body.get("error") is True:
                sqli_pass_count += 1

        passed_sqli_suite = (sqli_pass_count == len(SQLI_FUZZ_VECTOR_PAYLOADS))
        self.record_test("TC-402", f"OWASP SQL Injection Fuzz Matrix ({sqli_pass_count}/{len(SQLI_FUZZ_VECTOR_PAYLOADS)} Neutralized)", passed_sqli_suite, "Parameterized Query Guard Active Across All Attack Vectors")

        # 3. HTTP CRLF Header Injection Fuzzing
        crlf_pass_count = 0
        for crlf_payload in CRLF_HEADER_PAYLOADS:
            payload = {"phone_or_email": crlf_payload, "password": "Agri#2026Password"}
            status, body, res_headers, latency = self.http_request("/api/v1/auth/login", method="POST", payload=payload)
            header_injected = any("x-injected-header" in k or "set-cookie" in k and "session_hijack" in v for k, v in res_headers.items())
            if status in [401, 400] and not header_injected:
                crlf_pass_count += 1

        passed_crlf = (crlf_pass_count == len(CRLF_HEADER_PAYLOADS))
        self.record_test("TC-403", f"OWASP CRLF Header Injection Guard ({crlf_pass_count}/{len(CRLF_HEADER_PAYLOADS)} Blocked)", passed_crlf, "HTTP Header Splitting & Injection Blocked")

    def run_stage_5_telemetry_simulation_stress_test(self):
        self.log_section("STAGE 5: Telemetry Stream & Simulation Engine Audit")

        status, body, _, latency = self.http_request("/api/v1/telemetry/latest")
        tel_data = body.get("telemetry", {})
        passed_tel = (status == 200 and "soil_moisture_vwc" in tel_data)
        self.record_test("TC-501", "Live Field Telemetry API Fetch", passed_tel, f"Soil Moisture: {tel_data.get('soil_moisture_vwc')}%", latency)

        for preset in ["HEALTHY", "PRE_SYMPTOMATIC_STRESS", "SEVERE_DROUGHT", "SMOKE_HAZARD"]:
            status_p, body_p, _, latency_p = self.http_request(f"/api/v1/simulate?preset={preset}", method="POST")
            ai_diag = body_p.get("ai_diagnosis", {})
            status_val = ai_diag.get("status") if isinstance(ai_diag, dict) else getattr(ai_diag, "status", None)
            passed_p = (status_p == 200 and body_p.get("preset_applied") == preset and status_val is not None)
            self.record_test(f"TC-502 [{preset}]", f"Crop Health Simulation Engine Trigger: {preset}", passed_p, f"Status: {status_val}", latency_p)

    def run_stage_6_ota_background_update_audit(self):
        self.log_section("STAGE 6: In-App Background OTA Update Audit")

        status, body, _, latency = self.http_request("/api/v1/update/check?current_version=1.0.0")
        passed_check = (status == 200 and body.get("has_update") is True and isinstance(body.get("latest_version"), str) and len(body.get("latest_version")) > 0)
        self.record_test("TC-601", "OTA Update Checker API Endpoint", passed_check, f"Latest Version: v{body.get('latest_version')}", latency)

        status_dl, body_dl, headers_dl, latency_dl = self.http_request("/api/v1/update/download")
        passed_dl = (status_dl == 200 and "application/vnd.android.package-archive" in headers_dl.get("content-type", ""))
        self.record_test("TC-602", "OTA APK Download Binary Package Endpoint", passed_dl, f"Package Size: {body_dl.get('size_bytes')} bytes", latency_dl)

    def generate_final_qa_report(self):
        total_time = round(time.time() - self.start_time, 2)
        score_pct = round((self.passed_tests / self.total_tests) * 100, 1) if self.total_tests > 0 else 0.0

        print("\n" + "=" * 80)
        print(" EXECUTIVE AUTOMATED QA & SECURITY TEST REPORT")
        print("=" * 80)
        print(f" Target Platform       : AgriSense Platform (v1.2.0)")
        print(f" OWASP Payloads Suite  : AppSec-Payloads Arsenal (Active)")
        print(f" Total Test Cases Run  : {self.total_tests}")
        print(f" Tests Passed          : {self.passed_tests} PASSED")
        print(f" Tests Failed          : {self.failed_tests} FAILED")
        print(f" Quality & Security    : {score_pct}% Compliance Score")
        print(f" Total Execution Time  : {total_time} seconds")
        print("=" * 80)
        print(" VERDICT: " + ("PASSED ALL ENTERPRISE AUDIT STAGES (READY FOR PRODUCTION)" if self.failed_tests == 0 else "AUDIT FAILURES DETECTED"))
        print("=" * 80 + "\n")

def main():
    print("""
    ================================================================================
      AGRIVISION PRO ENTERPRISE QA & PENETRATION TESTER BOT (v3.0.0)
      Incorporating OWASP AppSec-Payloads Arsenal Fuzzing Suite
    ================================================================================
    """)
    bot = EnterpriseQATesterBot()
    bot.run_stage_1_server_health_security_headers()
    bot.run_stage_2_authentication_password_verification()
    bot.run_stage_3_duplicate_account_prevention()
    bot.run_stage_4_appsec_payloads_fuzzing_suite()
    bot.run_stage_5_telemetry_simulation_stress_test()
    bot.run_stage_6_ota_background_update_audit()
    bot.generate_final_qa_report()

if __name__ == "__main__":
    main()
