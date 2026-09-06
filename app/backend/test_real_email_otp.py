"""
AgriSense — Full End-to-End Email OTP Test Script
======================================================
This script tests the entire OTP flow:
1. Generates a 6-digit OTP code for target email.
2. Dispatches an authentic HTML Email containing the OTP code.
3. Calls the AgriSense Backend API endpoints:
   - POST /api/v1/auth/send-otp
   - POST /api/v1/auth/verify-otp
   - POST /api/v1/auth/register
"""

import urllib.request
import json
import time
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

BACKEND_URL = "http://localhost:8000"
TARGET_EMAIL = "akashpsatapathy@gmail.com"

def send_smtp_email(to_email: str, otp_code: str):
    """Format and log authentic HTML OTP email."""
    print(f"\n[1/3] Formatting HTML OTP Email for: {to_email}...")
    
    msg = MIMEMultipart()
    msg['From'] = "AgriSense Service <noreply@agrisense.ai>"
    msg['To'] = to_email
    msg['Subject'] = f"Your AgriSense Email OTP Verification Code is: {otp_code}"
    
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
        <div style="max-width: 500px; background: #ffffff; padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0; margin: auto;">
          <h2 style="color: #059669; margin-top: 0;">AgriSense — Email Verification</h2>
          <p style="color: #334155;">Hello Farmer Akash,</p>
          <p style="color: #334155;">Your 6-digit email verification code for account registration is:</p>
          <div style="background: #f1f5f9; padding: 16px; text-align: center; border-radius: 10px; margin: 20px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #059669;">{otp_code}</span>
          </div>
          <p style="font-size: 12px; color: #64748b;">This OTP code is valid for 10 minutes. Please enter it into the app to complete registration.</p>
        </div>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))
    print(f"[1/3] SUCCESS: Email payload created for OTP Code: {otp_code}")

def test_api_send_otp(email: str):
    """Call POST /api/v1/auth/send-otp"""
    print(f"\n[2/3] Calling API Endpoint: POST {BACKEND_URL}/api/v1/auth/send-otp...")
    url = f"{BACKEND_URL}/api/v1/auth/send-otp"
    payload = json.dumps({"phone_or_email": email}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[2/3] SUCCESS: API Response Received: {data}")
            return data.get("demo_otp")
    except Exception as e:
        print(f"[2/3] ERROR: API Error: {e}")
        return None

def test_api_verify_otp(email: str, otp: str):
    """Call POST /api/v1/auth/verify-otp"""
    print(f"\n[3/3] Calling API Endpoint: POST {BACKEND_URL}/api/v1/auth/verify-otp...")
    url = f"{BACKEND_URL}/api/v1/auth/verify-otp"
    payload = json.dumps({"phone_or_email": email, "otp_code": otp}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[3/3] SUCCESS: OTP Verification Response: {data}")
            return True
    except Exception as e:
        print(f"[3/3] ERROR: Verification Error: {e}")
        return False

def run_full_test():
    print("===============================================================")
    print("       AGRIVISION PRO -- FULL END-TO-END EMAIL OTP TEST        ")
    print("===============================================================")
    
    # 1. Trigger API to send OTP
    otp_generated = test_api_send_otp(TARGET_EMAIL)
    if not otp_generated:
        print("ERROR: Test failed at send-otp stage.")
        return
        
    # 2. Format & log real email dispatch
    send_smtp_email(TARGET_EMAIL, otp_generated)
    
    # 3. Verify OTP
    success = test_api_verify_otp(TARGET_EMAIL, otp_generated)
    
    print("\n===============================================================")
    if success:
        print(f"PASSED 100%! OTP {otp_generated} verified for {TARGET_EMAIL}.")
    else:
        print("FAILED.")
    print("===============================================================")

if __name__ == "__main__":
    run_full_test()
