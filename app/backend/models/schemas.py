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

class ResetPasswordRequest(BaseModel):
    phone_or_email: str
    new_password: str

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
    phone: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
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
from typing import Optional

import json

def _validate_polygon_coords(v):
    if v is None:
        return v
    try:
        coords = json.loads(v)
        if not isinstance(coords, list) or len(coords) < 3:
            raise ValueError("polygon_coords must be a JSON array with at least 3 points")
    except Exception:
        raise ValueError("polygon_coords must be valid JSON")
    return v

def _validate_acres(v):
    if v is not None and v <= 0:
        raise ValueError("acres must be greater than 0")
    return v

def _validate_non_empty_str(v):
    if v is not None and not v.strip():
        raise ValueError("String field cannot be empty")
    return v

def _validate_crop_status(v):
    if v is not None and v not in ("PLANTED", "HARVESTED", "FAILED"):
        raise ValueError("Invalid crop status")
    return v

class ZoneCreate(BaseModel):
    zone_name: str
    acres: float
    polygon_coords: str = "[]"

    @validator('zone_name')
    def validate_name(cls, v):
        return _validate_non_empty_str(v)

    @validator('acres')
    def validate_acres(cls, v):
        return _validate_acres(v)

    @validator('polygon_coords')
    def validate_polygon(cls, v):
        return _validate_polygon_coords(v)

class ZoneUpdate(BaseModel):
    zone_name: Optional[str] = None
    acres: Optional[float] = None
    polygon_coords: Optional[str] = None

    @validator('zone_name')
    def validate_name(cls, v):
        return _validate_non_empty_str(v)

    @validator('acres')
    def validate_acres(cls, v):
        return _validate_acres(v)

    @validator('polygon_coords')
    def validate_polygon(cls, v):
        return _validate_polygon_coords(v)

class CropCreate(BaseModel):
    crop_name: str
    status: str = "PLANTED"
    planted_date: Optional[float] = None

    @validator('crop_name')
    def validate_name(cls, v):
        return _validate_non_empty_str(v)

    @validator('status')
    def validate_status(cls, v):
        return _validate_crop_status(v)

class CropUpdate(BaseModel):
    crop_name: Optional[str] = None
    status: Optional[str] = None

    @validator('crop_name')
    def validate_name(cls, v):
        return _validate_non_empty_str(v)

    @validator('status')
    def validate_status(cls, v):
        return _validate_crop_status(v)

class DeviceAssignRequest(BaseModel):
    device_id: str
    zone_id: int
    device_type: str = "SENSOR"

class ChatbotQueryRequest(BaseModel):
    query: str
    language: Optional[str] = "auto"
    farm_id: Optional[int] = None
    location: Optional[str] = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    crop_type: Optional[str] = None
    image_base64: Optional[str] = None
    enable_web_search: Optional[bool] = True
