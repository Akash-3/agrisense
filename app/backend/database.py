import os
from dotenv import load_dotenv
load_dotenv()
import re
import sqlite3
import hashlib
import secrets
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# POSTGRES DB ENGINE CONNECTION WITH FALLBACK TO SQLITE
POSTGRES_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
IS_POSTGRES = bool(POSTGRES_URL)

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "agrisense_farmer.db"))

def get_db_connection():
    if IS_POSTGRES:
        import psycopg2
        url = POSTGRES_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        return conn
    else:
        return sqlite3.connect(DB_PATH, timeout=15.0, check_same_thread=False)

def format_query(sql: str) -> str:
    if IS_POSTGRES:
        return sql.replace("?", "%s")
    return sql

def execute_db(sql: str, params: tuple = (), fetchone: bool = False, fetchall: bool = False, commit: bool = False, return_lastrowid: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    formatted_sql = format_query(sql)
    
    if IS_POSTGRES and return_lastrowid and "RETURNING id" not in formatted_sql and formatted_sql.strip().upper().startswith("INSERT"):
        formatted_sql += " RETURNING id"
    
    cursor.execute(formatted_sql, params)
    
    res = None
    if return_lastrowid:
        if IS_POSTGRES:
            res = cursor.fetchone()[0]
        else:
            res = cursor.lastrowid
    elif fetchone:
        res = cursor.fetchone()
    elif fetchall:
        res = cursor.fetchall()
        
    if commit or return_lastrowid:
        conn.commit()
        
    conn.close()
    return res

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900

def init_db():
    if not IS_POSTGRES:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    if IS_POSTGRES:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id SERIAL PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            phone_or_email VARCHAR(255) UNIQUE NOT NULL,
            phone VARCHAR(100) DEFAULT '+1 (555) 019-2834',
            country VARCHAR(100) DEFAULT 'United States',
            country_code VARCHAR(20) DEFAULT '+1',
            address TEXT DEFAULT '',
            city VARCHAR(100) DEFAULT '',
            state VARCHAR(100) DEFAULT '',
            postal_code VARCHAR(50) DEFAULT '',
            password_hash TEXT NOT NULL,
            salt TEXT DEFAULT '',
            farm_name VARCHAR(255) DEFAULT 'Main Farm',
            gender VARCHAR(50) DEFAULT 'Farmer',
            age INTEGER DEFAULT 32,
            avatar_id INTEGER DEFAULT 1,
            created_at DOUBLE PRECISION NOT NULL,
            password_updated_at DOUBLE PRECISION DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS farms (
            id SERIAL PRIMARY KEY,
            farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
            farm_name VARCHAR(255) NOT NULL,
            farm_acres DOUBLE PRECISION DEFAULT 10.0,
            crop_type VARCHAR(255) DEFAULT 'Wheat & Paddy',
            created_at DOUBLE PRECISION NOT NULL
        );
        CREATE TABLE IF NOT EXISTS otp_codes (
            email_or_phone VARCHAR(255) PRIMARY KEY,
            otp_code VARCHAR(10) NOT NULL,
            expires_at DOUBLE PRECISION NOT NULL,
            attempts INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS login_attempts (
            identifier VARCHAR(255) PRIMARY KEY,
            failed_count INTEGER DEFAULT 0,
            last_failed_at DOUBLE PRECISION NOT NULL
        );
        CREATE TABLE IF NOT EXISTS auth_sessions (
            session_token VARCHAR(255) PRIMARY KEY,
            farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
            created_at DOUBLE PRECISION NOT NULL,
            expires_at DOUBLE PRECISION NOT NULL
        );
        """)
        for col, col_def in [
            ("phone", "VARCHAR(100) DEFAULT '+1 (555) 019-2834'"),
            ("country", "VARCHAR(100) DEFAULT 'United States'"),
            ("country_code", "VARCHAR(20) DEFAULT '+1'"),
            ("address", "TEXT DEFAULT ''"),
            ("city", "VARCHAR(100) DEFAULT ''"),
            ("state", "VARCHAR(100) DEFAULT ''"),
            ("postal_code", "VARCHAR(50) DEFAULT ''")
        ]:
            try:
                cursor.execute(f"ALTER TABLE farmers ADD COLUMN IF NOT EXISTS {col} {col_def};")
            except Exception:
                pass
    else:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone_or_email TEXT UNIQUE NOT NULL,
            phone TEXT DEFAULT '+1 (555) 019-2834',
            country TEXT DEFAULT 'United States',
            country_code TEXT DEFAULT '+1',
            address TEXT DEFAULT '',
            city TEXT DEFAULT '',
            state TEXT DEFAULT '',
            postal_code TEXT DEFAULT '',
            password_hash TEXT NOT NULL,
            salt TEXT DEFAULT '',
            farm_name TEXT DEFAULT 'Main Farm',
            gender TEXT DEFAULT 'Farmer',
            age INTEGER DEFAULT 32,
            avatar_id INTEGER DEFAULT 1,
            created_at REAL NOT NULL
        )
        """)
        cursor.execute("PRAGMA table_info(farmers)")
        columns = [col[1] for col in cursor.fetchall()]
        for col, col_def in [
            ('phone', "TEXT DEFAULT '+1 (555) 019-2834'"),
            ('country', "TEXT DEFAULT 'United States'"),
            ('country_code', "TEXT DEFAULT '+1'"),
            ('address', "TEXT DEFAULT ''"),
            ('city', "TEXT DEFAULT ''"),
            ('state', "TEXT DEFAULT ''"),
            ('postal_code', "TEXT DEFAULT ''"),
            ('salt', "TEXT DEFAULT ''"),
            ('farm_name', "TEXT DEFAULT 'Main Farm'"),
            ('gender', "TEXT DEFAULT 'Farmer'"),
            ('age', "INTEGER DEFAULT 32"),
            ('avatar_id', "INTEGER DEFAULT 1"),
            ('password_updated_at', "REAL DEFAULT NULL")
        ]:
            if col not in columns:
                try:
                    cursor.execute(f"ALTER TABLE farmers ADD COLUMN {col} {col_def}")
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
    row = execute_db("SELECT failed_count, last_failed_at FROM login_attempts WHERE identifier = ?", (identifier.lower(),), fetchone=True)
    if row:
        failed_count, last_failed_at = row[0], row[1]
        elapsed = time.time() - last_failed_at
        if failed_count >= MAX_LOGIN_ATTEMPTS and elapsed < LOCKOUT_DURATION:
            remaining_mins = int((LOCKOUT_DURATION - elapsed) // 60) + 1
            return True, remaining_mins
    return False, 0

def record_failed_attempt(identifier: str):
    row = execute_db("SELECT failed_count FROM login_attempts WHERE identifier = ?", (identifier.lower(),), fetchone=True)
    count = (row[0] + 1) if row else 1
    if IS_POSTGRES:
        execute_db(
            "INSERT INTO login_attempts (identifier, failed_count, last_failed_at) VALUES (?, ?, ?) ON CONFLICT (identifier) DO UPDATE SET failed_count = EXCLUDED.failed_count, last_failed_at = EXCLUDED.last_failed_at",
            (identifier.lower(), count, time.time()),
            commit=True
        )
    else:
        execute_db(
            "REPLACE INTO login_attempts (identifier, failed_count, last_failed_at) VALUES (?, ?, ?)",
            (identifier.lower(), count, time.time()),
            commit=True
        )

def clear_failed_attempts(identifier: str):
    execute_db("DELETE FROM login_attempts WHERE identifier = ?", (identifier.lower(),), commit=True)

def check_farmer_exists(phone_or_email: str) -> bool:
    clean_id = phone_or_email.strip().lower()
    row = execute_db("SELECT id FROM farmers WHERE LOWER(phone_or_email) = ?", (clean_id,), fetchone=True)
    return row is not None

def send_real_email_otp(to_email: str, otp_code: str, full_name: str = "Farmer"):
    greeting_name = full_name.strip() if full_name and full_name.strip() else "Farmer"
    print(f"\n[GMAIL SMTP SERVICE] Sending Personalized OTP Email to: {greeting_name} ({to_email}) | Code: {otp_code}")

    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        print("[SMTP FATAL ERROR] Missing SMTP_EMAIL or SMTP_APP_PASSWORD in environment.")
        raise ValueError("Server configuration error: Email functionality is currently unavailable.")

    msg = MIMEMultipart()
    msg['From'] = f"AgriSense Support <{SMTP_EMAIL}>"
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
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.sendmail(SMTP_EMAIL, [to_email], msg.as_string())
        server.quit()
        print(f"[GMAIL SMTP SUCCESS] REAL PERSONALIZED OTP EMAIL DISPATCHED TO GMAIL INBOX: {to_email}")
    except Exception as e:
        print(f"[GMAIL SMTP ERROR] {e}")

def generate_otp(email_or_phone: str, full_name: str = "Farmer") -> str:
    clean_id = email_or_phone.strip().lower()
    otp = str(random.randint(100000, 999999))
    expires = time.time() + 600
    if IS_POSTGRES:
        execute_db(
            "INSERT INTO otp_codes (email_or_phone, otp_code, expires_at, attempts) VALUES (?, ?, ?, 0) ON CONFLICT (email_or_phone) DO UPDATE SET otp_code = EXCLUDED.otp_code, expires_at = EXCLUDED.expires_at, attempts = 0",
            (clean_id, otp, expires),
            commit=True
        )
    else:
        execute_db(
            "REPLACE INTO otp_codes (email_or_phone, otp_code, expires_at, attempts) VALUES (?, ?, ?, 0)",
            (clean_id, otp, expires),
            commit=True
        )
    
    if "@" in clean_id:
        send_real_email_otp(clean_id, otp, full_name=full_name)
        
    return otp

def verify_otp(email_or_phone: str, otp_code: str) -> bool:
    clean_id = email_or_phone.strip().lower()
    row = execute_db("SELECT otp_code, expires_at, attempts FROM otp_codes WHERE LOWER(email_or_phone) = ?", (clean_id,), fetchone=True)
    
    if not row:
        return False
        
    stored_otp, expires_at, attempts = row[0], row[1], row[2]
    
    if time.time() > expires_at or attempts >= 5:
        return False
        
    execute_db("UPDATE otp_codes SET attempts = attempts + 1 WHERE LOWER(email_or_phone) = ?", (clean_id,), commit=True)
    
    if stored_otp == otp_code:
        execute_db("DELETE FROM otp_codes WHERE LOWER(email_or_phone) = ?", (clean_id,), commit=True)
        return True
        
    return False

def register_farmer(full_name: str, phone_or_email: str, farm_name: str = "Main Farm", farm_acres: float = 10.0, password: str = "", gender: str = "Farmer", age: int = 32, avatar_id: int = 1, crop_type: str = "Wheat & Paddy", phone: str = "+1 (555) 019-2834"):
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

    try:
        farmer_id = execute_db(
            "INSERT INTO farmers (full_name, phone_or_email, phone, password_hash, salt, farm_name, gender, age, avatar_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (full_name, clean_id, phone, pwd_hash, salt, farm_name, gender, age, avatar_id, time.time()),
            return_lastrowid=True
        )
        execute_db(
            "INSERT INTO farms (farmer_id, farm_name, farm_acres, crop_type, created_at) VALUES (?, ?, ?, ?, ?)",
            (farmer_id, farm_name, farm_acres, crop_type, time.time()),
            commit=True
        )
        
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
    except Exception as err:
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

    row = execute_db(
        "SELECT id, full_name, password_hash, salt, gender, age, avatar_id, password_updated_at, phone, country, country_code, address, city, state, postal_code FROM farmers WHERE LOWER(phone_or_email) = ?",
        (clean_id,),
        fetchone=True
    )
    
    if row:
        farmer_id = row[0]
        full_name = row[1]
        stored_hash = row[2]
        salt = row[3] if len(row) > 3 and row[3] else ""
        gender = row[4] if len(row) > 4 and row[4] else "Farmer"
        age = row[5] if len(row) > 5 and row[5] else 32
        avatar_id = row[6] if len(row) > 6 and row[6] else 1
        password_updated_at = row[7] if len(row) > 7 else None
        phone = row[8] if len(row) > 8 and row[8] else "+1 (555) 019-2834"
        country = row[9] if len(row) > 9 and row[9] else "United States"
        country_code = row[10] if len(row) > 10 and row[10] else "+1"
        address = row[11] if len(row) > 11 and row[11] else ""
        city = row[12] if len(row) > 12 and row[12] else ""
        state = row[13] if len(row) > 13 and row[13] else ""
        postal_code = row[14] if len(row) > 14 and row[14] else ""
        
        computed_hash = hash_password(password, salt) if salt else hash_password(password)
        salt_bytes = salt.encode('utf-8') if salt else b''
        legacy_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, 100000).hex() if salt else hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        if computed_hash == stored_hash or legacy_hash == stored_hash or hash_password(password) == stored_hash:
            clear_failed_attempts(clean_id)
            farm_rows = execute_db("SELECT id, farm_name, farm_acres, crop_type FROM farms WHERE farmer_id = ?", (farmer_id,), fetchall=True)
            farms = [{"id": f[0], "farm_name": f[1], "farm_acres": f[2], "crop_type": f[3]} for f in (farm_rows or [])]
            
            token = create_session_token(farmer_id)
            return {
                "status": "success",
                "session_token": token,
                "farmer": {
                    "id": farmer_id,
                    "full_name": full_name,
                    "phone_or_email": clean_id,
                    "phone": phone,
                    "country": country,
                    "country_code": country_code,
                    "address": address,
                    "city": city,
                    "state": state,
                    "postal_code": postal_code,
                    "gender": gender,
                    "age": age,
                    "avatar_id": avatar_id,
                    "password_updated_at": password_updated_at,
                    "farms": farms
                }
            }

    record_failed_attempt(clean_id)
    return {"status": "error", "message": "Invalid mobile number/email or password!"}

def reset_password_with_otp(phone_or_email: str, new_password: str, otp_code: str) -> dict:
    clean_id = phone_or_email.strip().lower()
    
    if not verify_otp(clean_id, otp_code):
        return {"status": "error", "message": "Invalid or expired OTP code!"}
        
    valid, msg = validate_password_strength(new_password)
    if not valid:
        return {"status": "error", "message": msg}
        
    row = execute_db("SELECT id FROM farmers WHERE LOWER(phone_or_email) = ?", (clean_id,), fetchone=True)
    if not row:
        return {"status": "error", "message": f"No account registered with '{clean_id}'."}
        
    salt = generate_salt()
    pwd_hash = hash_password(new_password, salt)
    now = time.time()
    
    execute_db("UPDATE farmers SET password_hash = ?, salt = ?, password_updated_at = ? WHERE LOWER(phone_or_email) = ?", (pwd_hash, salt, now, clean_id), commit=True)
    clear_failed_attempts(clean_id)
    return {"status": "success", "message": "Password reset successfully! You can now log in with your new password.", "password_updated_at": now}

def create_session_token(farmer_id: int) -> str:
    token = secrets.token_hex(32)
    expires = time.time() + 86400 * 30 # 30 Days
    execute_db(
        "INSERT INTO auth_sessions (session_token, farmer_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, farmer_id, time.time(), expires),
        commit=True
    )
    return token

def add_farm(farmer_id: int, farm_name: str, farm_acres: float, crop_type: str):
    farm_id = execute_db(
        "INSERT INTO farms (farmer_id, farm_name, farm_acres, crop_type, created_at) VALUES (?, ?, ?, ?, ?)",
        (farmer_id, farm_name, farm_acres, crop_type, time.time()),
        return_lastrowid=True
    )
    return {"status": "success", "farm_id": farm_id}

def update_farmer_profile(farmer_id: int, full_name: str, phone_or_email: str = None, farm_name: str = None, farm_acres: float = None, crop_type: str = None, new_password: str = None, gender: str = "Farmer", age: int = 32, avatar_id: int = 1, location: str = None, phone: str = None, country: str = None, country_code: str = None, address: str = None, city: str = None, state: str = None, postal_code: str = None):
    fields = ["full_name = ?", "gender = ?", "age = ?", "avatar_id = ?"]
    params = [full_name, gender, age, avatar_id]
    updated_at_val = None

    if phone:
        fields.append("phone = ?")
        params.append(phone.strip())

    if country:
        fields.append("country = ?")
        params.append(country.strip())

    if country_code:
        fields.append("country_code = ?")
        params.append(country_code.strip())

    if address is not None:
        fields.append("address = ?")
        params.append(address.strip())

    if city is not None:
        fields.append("city = ?")
        params.append(city.strip())

    if state is not None:
        fields.append("state = ?")
        params.append(state.strip())

    if postal_code is not None:
        fields.append("postal_code = ?")
        params.append(postal_code.strip())

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
    execute_db(query, tuple(params), commit=True)

    if farm_name or farm_acres or crop_type:
        execute_db("UPDATE farms SET farm_name = COALESCE(?, farm_name), farm_acres = COALESCE(?, farm_acres), crop_type = COALESCE(?, crop_type) WHERE farmer_id = ?", (farm_name, farm_acres, crop_type, farmer_id), commit=True)

    row = execute_db("SELECT phone_or_email, phone, country, country_code, address, city, state, postal_code FROM farmers WHERE id = ?", (farmer_id,), fetchone=True)
    stored_email = row[0] if row else phone_or_email
    stored_phone = row[1] if row and len(row) > 1 and row[1] else (phone or "+1 (555) 019-2834")
    stored_country = row[2] if row and len(row) > 2 and row[2] else (country or "United States")
    stored_country_code = row[3] if row and len(row) > 3 and row[3] else (country_code or "+1")
    stored_address = row[4] if row and len(row) > 4 and row[4] else (address or "")
    stored_city = row[5] if row and len(row) > 5 and row[5] else (city or "")
    stored_state = row[6] if row and len(row) > 6 and row[6] else (state or "")
    stored_postal_code = row[7] if row and len(row) > 7 and row[7] else (postal_code or "")

    return {
        "status": "success",
        "message": "Profile & Farm details updated in database successfully!",
        "farmer": {
            "id": farmer_id,
            "full_name": full_name,
            "phone_or_email": stored_email,
            "phone": stored_phone,
            "country": stored_country,
            "country_code": stored_country_code,
            "address": stored_address,
            "city": stored_city,
            "state": stored_state,
            "postal_code": stored_postal_code,
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
