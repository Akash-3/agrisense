from typing import Optional
from pydantic import BaseModel, validator
from database import sanitize_input
from config import sanitize_email_or_phone

class RegisterRequest(BaseModel):
    full_name: str
    phone_or_email: str
    farm_name: str = "Main Farm"
    farm_acres: float = 10.0
    password: str
    gender: str = "Farmer"
    age: int = 32
    avatar_id: int = 1
    crop_type: str = "Wheat & Paddy"

    @validator('full_name', 'farm_name', 'crop_type')
    def sanitize_fields(cls, v):
        return sanitize_input(v)

    @validator('phone_or_email')
    def sanitize_email(cls, v):
        return sanitize_email_or_phone(v)

class LoginRequest(BaseModel):
    phone_or_email: str
    password: str

    @validator('phone_or_email')
    def sanitize_email(cls, v):
        return sanitize_email_or_phone(v)

class SSORequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_id: Optional[int] = 1
    farm_name: Optional[str] = None
    farm_acres: Optional[float] = None
    crop_type: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None

class OTPRequest(BaseModel):
    phone_or_email: str
    full_name: str = "Farmer"

    @validator('full_name')
    def sanitize_fields(cls, v):
        return sanitize_input(v)

    @validator('phone_or_email')
    def sanitize_email(cls, v):
        return sanitize_email_or_phone(v)

class VerifyOTPRequest(BaseModel):
    phone_or_email: str
    otp_code: str

    @validator('otp_code')
    def sanitize_fields(cls, v):
        return sanitize_input(v)

    @validator('phone_or_email')
    def sanitize_email(cls, v):
        return sanitize_email_or_phone(v)

class ResetPasswordRequest(BaseModel):
    phone_or_email: str
    new_password: str
    otp_code: str

    @validator('otp_code')
    def sanitize_fields(cls, v):
        return sanitize_input(v)

    @validator('phone_or_email')
    def sanitize_email(cls, v):
        return sanitize_email_or_phone(v)

class AddFarmRequest(BaseModel):
    farmer_id: int
    farm_name: str
    farm_acres: float = 10.0
    crop_type: str = "Wheat & Paddy"

    @validator('farm_name', 'crop_type')
    def sanitize_fields(cls, v):
        return sanitize_input(v)

class UpdateProfileRequest(BaseModel):
    farmer_id: int = 1
    full_name: str
    phone_or_email: Optional[str] = None
    farm_name: Optional[str] = None
    farm_acres: Optional[float] = None
    crop_type: Optional[str] = None
    location: Optional[str] = None
    new_password: Optional[str] = None
    gender: str = "Farmer"
    age: int = 32
    avatar_id: int = 1

    @validator('full_name', 'gender')
    def sanitize_fields(cls, v):
        return sanitize_input(v)

class ESP32TelemetryIngest(BaseModel):
    device_id: str = "ESP32_SOIL_NODE_01"
    soil_moisture: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    smoke_ppm: Optional[float] = None
    soil_status: Optional[str] = "ONLINE"
    dht_status: Optional[str] = "ONLINE"
    mq135_status: Optional[str] = "ONLINE"
    api_key: Optional[str] = None

class CropImageDiagnosisRequest(BaseModel):
    crop_type: Optional[str] = "Wheat & Paddy"
    image_base64: Optional[str] = None
    note: Optional[str] = None
