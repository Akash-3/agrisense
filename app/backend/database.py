import os
import re
import sqlite3
import hashlib
import secrets
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "agrisense_farmer.db"))

# LIVE GMAIL SMTP CREDENTIALS WITH ENVIRONMENT VARIABLE OVERRIDES
GMAIL_SENDER = os.getenv("GMAIL_SENDER", "agrisense.support.tcsc@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "rjfomljidtgtvgcw")

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900 # 15 minutes in seconds

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS farmers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        phone_or_email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT DEFAULT '',
        farm_name TEXT DEFAULT 'Main Farm',
        gender TEXT DEFAULT 'Farmer',
        age INTEGER DEFAULT 32,
        avatar_id INTEGER DEFAULT 1,
        created_at REAL NOT NULL
    )
    """)
    # Migration column check
    cursor.execute("PRAGMA table_info(farmers)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'salt' not in columns:
        try:
            cursor.execute("ALTER TABLE farmers ADD COLUMN salt TEXT DEFAULT ''")
        except Exception:
            pass
    if 'farm_name' not in columns:
        try:
            cursor.execute("ALTER TABLE farmers ADD COLUMN farm_name TEXT DEFAULT 'Main Farm'")
        except Exception:
            pass
    if 'gender' not in columns:
        try:
            cursor.execute("ALTER TABLE farmers ADD COLUMN gender TEXT DEFAULT 'Farmer'")
        except Exception:
            pass
    if 'age' not in columns:
        try:
            cursor.execute("ALTER TABLE farmers ADD COLUMN age INTEGER DEFAULT 32")
        except Exception:
            pass
    if 'avatar_id' not in columns:
        try:
            cursor.execute("ALTER TABLE farmers ADD COLUMN avatar_id INTEGER DEFAULT 1")
        except Exception:
            pass
    if 'password_updated_at' not in columns:
        try:
            cursor.execute("ALTER TABLE farmers ADD COLUMN password_updated_at REAL DEFAULT NULL")
        except Exception:
            pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS farms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER NOT NULL,
        farm_name TEXT NOT NULL,
        farm_acres REAL DEFAULT 10.0,
        crop_type TEXT DEFAULT 'Wheat & Paddy',
        created_at REAL NOT NULL,
        FOREIGN KEY(farmer_id) REFERENCES farmers(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS otp_codes (
        email_or_phone TEXT PRIMARY KEY,
        otp_code TEXT NOT NULL,
        expires_at REAL NOT NULL,
        attempts INTEGER DEFAULT 0
    )
    """)
    cursor.execute("PRAGMA table_info(otp_codes)")
    otp_cols = [c[1] for c in cursor.fetchall()]
    if 'attempts' not in otp_cols:
        try:
            cursor.execute("ALTER TABLE otp_codes ADD COLUMN attempts INTEGER DEFAULT 0")
        except Exception:
            pass
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS login_attempts (
        identifier TEXT PRIMARY KEY,
        failed_count INTEGER DEFAULT 0,
        last_failed_at REAL NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auth_sessions (
        session_token TEXT PRIMARY KEY,
        farmer_id INTEGER NOT NULL,
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL,
        FOREIGN KEY(farmer_id) REFERENCES farmers(id)
    )
    """)
    conn.commit()
    conn.close()

def sanitize_input(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'<[^>]*>', '', str(text))
    text = re.sub(r'javascript\s*:', '', text, flags=re.IGNORECASE)
    text = text.replace("'", "''")
    return text.strip()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "agrisense_jwt_enterprise_secret_2026_key_#9821!")

def generate_salt() -> str:
    return secrets.token_hex(16)

def hash_password(password: str, salt: str = "") -> str:
    # Keyed PBKDF2 HMAC-SHA256 combined with JWT Server Secret Key for high security
    keyed_pass = f"{password}:{JWT_SECRET_KEY}".encode('utf-8')
    salt_bytes = salt.encode('utf-8') if salt else b'default_agrisense_salt'
    return hashlib.pbkdf2_hmac('sha256', keyed_pass, salt_bytes, 100000).hex()

def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least 1 uppercase letter (A-Z)."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least 1 lowercase letter (a-z)."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least 1 digit (0-9)."
    if not re.search(r'[@#$%^&*!_\-+=\[\]{}|:<>,.?/]', password):
        return False, "Password must contain at least 1 special character (@#$%^&*!)."
    return True, "Password is strong."

def is_account_locked(identifier: str) -> tuple[bool, int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT failed_count, last_failed_at FROM login_attempts WHERE identifier = ?", (identifier.lower(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        failed_count, last_failed_at = row[0], row[1]
        elapsed = time.time() - last_failed_at
        if failed_count >= MAX_LOGIN_ATTEMPTS and elapsed < LOCKOUT_DURATION:
            remaining_mins = int((LOCKOUT_DURATION - elapsed) // 60) + 1
            return True, remaining_mins
    return False, 0

def record_failed_attempt(identifier: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT failed_count FROM login_attempts WHERE identifier = ?", (identifier.lower(),))
    row = cursor.fetchone()
    count = (row[0] + 1) if row else 1
    cursor.execute(
        "REPLACE INTO login_attempts (identifier, failed_count, last_failed_at) VALUES (?, ?, ?)",
        (identifier.lower(), count, time.time())
    )
    conn.commit()
    conn.close()

def clear_failed_attempts(identifier: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM login_attempts WHERE identifier = ?", (identifier.lower(),))
    conn.commit()
    conn.close()

def check_farmer_exists(phone_or_email: str) -> bool:
    clean_id = phone_or_email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM farmers WHERE LOWER(phone_or_email) = ?", (clean_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def send_real_email_otp(to_email: str, otp_code: str, full_name: str = "Farmer"):
    greeting_name = full_name.strip() if full_name and full_name.strip() else "Farmer"
    print(f"\n[GMAIL SMTP SERVICE] Sending Personalized OTP Email to: {greeting_name} ({to_email}) | Code: {otp_code}")

    msg = MIMEMultipart()
    msg['From'] = f"AgriSense Support <{GMAIL_SENDER}>"
    msg['To'] = to_email
    msg['Subject'] = f"Hello {greeting_name}, Your AgriSense Verification Code is: {otp_code}"
    
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
        <div style="max-width: 500px; background: #ffffff; padding: 24px; border-radius: 14px; border: 1px solid #e2e8f0; margin: auto;">
          <h2 style="color: #059669; margin-top: 0;">AgriSense -- Email Verification</h2>
          <p style="color: #334155; font-size: 15px; font-weight: bold;">Hello {greeting_name},</p>
          <p style="color: #334155;">Your 6-digit email verification code for account registration is:</p>
          <div style="background: #f1f5f9; padding: 18px; text-align: center; border-radius: 10px; margin: 20px 0;">
            <span style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #059669;">{otp_code}</span>
          </div>
          <p style="font-size: 12px; color: #64748b;">This OTP code is valid for 10 minutes. Enter it into your AgriSense app to complete registration.</p>
        </div>
      </body>
    </html>
    """
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12)
        server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_SENDER, [to_email], msg.as_string())
        server.quit()
        print(f"[GMAIL SMTP SUCCESS] REAL PERSONALIZED OTP EMAIL DISPATCHED TO GMAIL INBOX: {to_email}")
    except Exception as e:
        print(f"[GMAIL SMTP ERROR] {e}")

def generate_otp(email_or_phone: str, full_name: str = "Farmer") -> str:
    clean_id = email_or_phone.strip().lower()
    otp = str(random.randint(100000, 999999))
    expires = time.time() + 600
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "REPLACE INTO otp_codes (email_or_phone, otp_code, expires_at, attempts) VALUES (?, ?, ?, 0)",
        (clean_id, otp, expires)
    )
    conn.commit()
    conn.close()
    
    if "@" in clean_id:
        send_real_email_otp(clean_id, otp, full_name=full_name)
        
    return otp

def verify_otp(email_or_phone: str, otp_code: str) -> bool:
    clean_id = email_or_phone.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT otp_code, expires_at, attempts FROM otp_codes WHERE LOWER(email_or_phone) = ?", (clean_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return False
        
    stored_otp, expires_at, attempts = row[0], row[1], row[2]
    
    if time.time() > expires_at or attempts >= 5:
        conn.close()
        return False
        
    cursor.execute("UPDATE otp_codes SET attempts = attempts + 1 WHERE LOWER(email_or_phone) = ?", (clean_id,))
    conn.commit()
    
    if stored_otp == otp_code:
        cursor.execute("DELETE FROM otp_codes WHERE LOWER(email_or_phone) = ?", (clean_id,))
        conn.commit()
        conn.close()
        return True
        
    conn.close()
    return False

def register_farmer(full_name: str, phone_or_email: str, farm_name: str = "Main Farm", farm_acres: float = 10.0, password: str = "", gender: str = "Farmer", age: int = 32, avatar_id: int = 1, crop_type: str = "Wheat & Paddy"):
    clean_id = phone_or_email.strip().lower()
    
    is_valid, msg = validate_password_strength(password)
    if not is_valid:
        return {"status": "error", "message": msg}

    if check_farmer_exists(clean_id):
        return {
            "status": "error",
            "message": f"Account Already Exists: '{clean_id}' is already registered! Please switch to the Login tab to sign in."
        }

    salt = generate_salt()
    pwd_hash = hash_password(password, salt)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO farmers (full_name, phone_or_email, password_hash, salt, farm_name, gender, age, avatar_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (full_name, clean_id, pwd_hash, salt, farm_name, gender, age, avatar_id, time.time())
        )
        farmer_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO farms (farmer_id, farm_name, farm_acres, crop_type, created_at) VALUES (?, ?, ?, ?, ?)",
            (farmer_id, farm_name, farm_acres, crop_type, time.time())
        )
        conn.commit()
        conn.close()
        
        session_token = create_session_token(farmer_id)
        return {
            "status": "success",
            "farmer_id": farmer_id,
            "full_name": full_name,
            "farm_name": farm_name,
            "gender": gender,
            "age": age,
            "avatar_id": avatar_id,
            "session_token": session_token
        }
    except sqlite3.IntegrityError:
        conn.close()
        return {
            "status": "error",
            "message": f"Account Already Exists: '{clean_id}' is already registered! Please switch to the Login tab to sign in."
        }
    except Exception as err:
        conn.close()
        print(f"[REGISTER DB EXCEPTION] {err}")
        return {
            "status": "error",
            "message": f"Registration Error: {err}"
        }

def login_farmer(phone_or_email: str, password: str):
    clean_id = phone_or_email.strip().lower()
    
    locked, remaining_mins = is_account_locked(clean_id)
    if locked:
        return {
            "status": "error",
            "message": f"Account Locked: Too many failed attempts. Try again in {remaining_mins} minutes."
        }

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, full_name, password_hash, salt, gender, age, avatar_id, password_updated_at FROM farmers WHERE LOWER(phone_or_email) = ?",
        (clean_id,)
    )
    row = cursor.fetchone()
    
    if row:
        farmer_id = row[0]
        full_name = row[1]
        stored_hash = row[2]
        salt = row[3] if len(row) > 3 and row[3] else ""
        gender = row[4] if len(row) > 4 and row[4] else "Farmer"
        age = row[5] if len(row) > 5 and row[5] else 32
        avatar_id = row[6] if len(row) > 6 and row[6] else 1
        password_updated_at = row[7] if len(row) > 7 else None
        
        computed_hash = hash_password(password, salt) if salt else hash_password(password)
        salt_bytes = salt.encode('utf-8') if salt else b''
        legacy_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, 100000).hex() if salt else hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        if computed_hash == stored_hash or legacy_hash == stored_hash or hash_password(password) == stored_hash:
            clear_failed_attempts(clean_id)
            cursor.execute("SELECT id, farm_name, farm_acres, crop_type FROM farms WHERE farmer_id = ?", (farmer_id,))
            farms = [{"id": f[0], "farm_name": f[1], "farm_acres": f[2], "crop_type": f[3]} for f in cursor.fetchall()]
            conn.close()
            
            token = create_session_token(farmer_id)
            return {
                "status": "success",
                "session_token": token,
                "farmer": {
                    "id": farmer_id,
                    "full_name": full_name,
                    "phone_or_email": clean_id,
                    "gender": gender,
                    "age": age,
                    "avatar_id": avatar_id,
                    "password_updated_at": password_updated_at,
                    "farms": farms
                }
            }

    conn.close()
    record_failed_attempt(clean_id)
    return {"status": "error", "message": "Invalid mobile number/email or password!"}

def reset_password_with_otp(phone_or_email: str, new_password: str, otp_code: str) -> dict:
    clean_id = phone_or_email.strip().lower()
    
    # 1. Verify OTP Code
    if not verify_otp(clean_id, otp_code):
        return {"status": "error", "message": "Invalid or expired OTP code!"}
        
    # 2. Validate Password Strength
    valid, msg = validate_password_strength(new_password)
    if not valid:
        return {"status": "error", "message": msg}
        
    # 3. Check Farmer Account Exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM farmers WHERE LOWER(phone_or_email) = ?", (clean_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"status": "error", "message": f"No account registered with '{clean_id}'."}
        
    # 4. Hash New Password with Salt & Server JWT Secret Key
    salt = generate_salt()
    pwd_hash = hash_password(new_password, salt)
    now = time.time()
    
    cursor.execute("UPDATE farmers SET password_hash = ?, salt = ?, password_updated_at = ? WHERE LOWER(phone_or_email) = ?", (pwd_hash, salt, now, clean_id))
    conn.commit()
    conn.close()
    
    clear_failed_attempts(clean_id)
    return {"status": "success", "message": "Password reset successfully! You can now log in with your new password.", "password_updated_at": now}

def create_session_token(farmer_id: int) -> str:
    token = secrets.token_hex(32)
    expires = time.time() + 86400 * 30 # 30 Days
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO auth_sessions (session_token, farmer_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, farmer_id, time.time(), expires)
    )
    conn.commit()
    conn.close()
    return token

def add_farm(farmer_id: int, farm_name: str, farm_acres: float, crop_type: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO farms (farmer_id, farm_name, farm_acres, crop_type, created_at) VALUES (?, ?, ?, ?, ?)",
        (farmer_id, farm_name, farm_acres, crop_type, time.time())
    )
    conn.commit()
    farm_id = cursor.lastrowid
    conn.close()
    return {"status": "success", "farm_id": farm_id}

def update_farmer_profile(farmer_id: int, full_name: str, phone_or_email: str = None, farm_name: str = None, farm_acres: float = None, crop_type: str = None, new_password: str = None, gender: str = "Farmer", age: int = 32, avatar_id: int = 1, location: str = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    fields = ["full_name = ?", "gender = ?", "age = ?", "avatar_id = ?"]
    params = [full_name, gender, age, avatar_id]
    updated_at_val = None

    if phone_or_email:
        fields.append("phone_or_email = ?")
        params.append(phone_or_email.strip().lower())

    if farm_name:
        fields.append("farm_name = ?")
        params.append(farm_name)

    if new_password and len(new_password) >= 6:
        salt = generate_salt()
        pwd_hash = hash_password(new_password, salt)
        updated_at_val = time.time()
        fields.append("password_hash = ?")
        fields.append("salt = ?")
        fields.append("password_updated_at = ?")
        params.extend([pwd_hash, salt, updated_at_val])

    params.append(farmer_id)
    query = f"UPDATE farmers SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, tuple(params))

    if farm_name or farm_acres or crop_type:
        cursor.execute("UPDATE farms SET farm_name = COALESCE(?, farm_name), farm_acres = COALESCE(?, farm_acres), crop_type = COALESCE(?, crop_type) WHERE farmer_id = ?", (farm_name, farm_acres, crop_type, farmer_id))

    conn.commit()
    conn.close()
    return {
        "status": "success",
        "message": "Profile & Farm details updated in database successfully!",
        "farmer": {
            "id": farmer_id,
            "full_name": full_name,
            "phone_or_email": phone_or_email,
            "farm_name": farm_name,
            "farm_acres": farm_acres,
            "crop_type": crop_type,
            "gender": gender,
            "age": age,
            "avatar_id": avatar_id,
            "password_updated_at": updated_at_val
        }
    }

# Run table initialization on module load
init_db()

# Run table initialization on module load
init_db()
