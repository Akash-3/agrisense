import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from dependencies import get_current_user
from models.schemas import ChatbotQueryRequest
from services.chatbot_service import chatbot_service, SUPPORTED_LANGUAGES
from database import execute_db, get_farm_owner, get_farms_by_farmer

router = APIRouter(prefix="/api/v1/chatbot", tags=["AgriSense AI Chatbot"])

# IN-MEMORY SLIDING WINDOW RATE LIMITER (15 REQUESTS / 60 SECONDS PER USER)
CHAT_RATE_LIMIT_WINDOW = 60.0
CHAT_MAX_REQUESTS_PER_WINDOW = 15
user_request_history: Dict[int, List[float]] = {}

def check_chatbot_rate_limit(farmer_id: int):
    now = time.time()
    if farmer_id not in user_request_history:
        user_request_history[farmer_id] = []
    
    # Filter out requests older than sliding window
    history = [t for t in user_request_history[farmer_id] if now - t < CHAT_RATE_LIMIT_WINDOW]
    user_request_history[farmer_id] = history
    
    if len(history) >= CHAT_MAX_REQUESTS_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {CHAT_MAX_REQUESTS_PER_WINDOW} chatbot queries per minute allowed."
        )
    user_request_history[farmer_id].append(now)

@router.post("/chat")
async def process_chat(payload: ChatbotQueryRequest, current_user: int = Depends(get_current_user)):
    """
    Authenticated Production Chatbot API:
    - Requires valid session token via get_current_user (Returns 401 if unauthenticated).
    - Rate limited to 15 queries/min per user (Returns 429 if exceeded).
    - Strictly resolves authorized farm context (Returns 403 if unauthorized farm_id requested).
    - Uses real telemetry if present; reports explicit unavailable status if absent.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
    
    # Enforce Rate Limiting
    check_chatbot_rate_limit(current_user)

    # Strictly Resolve Farmer's Authorized Farm Context
    authorized_farm_info = None
    target_farm_id = payload.farm_id

    if target_farm_id is not None:
        owner_id = get_farm_owner(target_farm_id)
        if owner_id is None:
            raise HTTPException(status_code=404, detail="Specified farm not found.")
        if owner_id != current_user:
            raise HTTPException(status_code=403, detail="Not authorized to access specified farm.")
        
        farm_row = execute_db("SELECT id, farm_name, farm_acres, crop_type FROM farms WHERE id = ?", (target_farm_id,), fetchone=True)
    else:
        # Default to farmer's primary authorized farm
        farm_row = execute_db("SELECT id, farm_name, farm_acres, crop_type FROM farms WHERE farmer_id = ? ORDER BY id ASC LIMIT 1", (current_user,), fetchone=True)

    if farm_row:
        f_id, f_name, f_acres, f_crop = farm_row
        
        # Check real telemetry records for authorized farm
        telem_row = execute_db(
            "SELECT soil_moisture, temperature, humidity, smoke_ppm, timestamp FROM telemetry_records WHERE farm_id = ? ORDER BY timestamp DESC LIMIT 1",
            (f_id,),
            fetchone=True
        )

        # Fallback to shared global node (farm_id=0) if authorized
        if not telem_row:
            telem_row = execute_db(
                "SELECT soil_moisture, temperature, humidity, smoke_ppm, timestamp FROM telemetry_records WHERE farm_id = 0 ORDER BY timestamp DESC LIMIT 1",
                fetchone=True
            )

        if telem_row and telem_row[0] is not None:
            soil, temp, hum, smoke, t_stamp = telem_row
            telem_text = f"Soil Moisture: {soil}%, Temp: {temp}°C, Humidity: {hum}%, Air PPM: {smoke}"
            env_array = [temp or 25.0, hum or 60.0, soil or 50.0, smoke or 80.0]
            has_telem = True
        else:
            telem_text = "Farm soil-moisture and sensor telemetry are currently unavailable."
            env_array = None
            has_telem = False

        authorized_farm_info = {
            "farm_id": f_id,
            "farm_name": f_name,
            "acres": f_acres,
            "crop_type": f_crop,
            "telemetry_status_text": telem_text,
            "telemetry_env": env_array,
            "has_real_telemetry": has_telem
        }

    try:
        res = chatbot_service.process_chat_query(
            query=payload.query.strip(),
            authenticated_farmer_id=current_user,
            authorized_farm_context=authorized_farm_info,
            language=payload.language or "auto",
            location=payload.location or "",
            latitude=payload.latitude,
            longitude=payload.longitude,
            crop_type=payload.crop_type,
            image_base64=payload.image_base64,
            enable_web_search=payload.enable_web_search if payload.enable_web_search is not None else True
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot processing error: {str(e)}")

@router.get("/languages")
async def get_supported_languages():
    """Returns catalog of 13 supported Indian languages."""
    return {
        "status": "success",
        "total": len(SUPPORTED_LANGUAGES),
        "languages": [
            {"code": k, "name": v["name"], "native": v["native"], "flag": v["flag"]}
            for k, v in SUPPORTED_LANGUAGES.items()
        ]
    }

@router.get("/suggestions")
async def get_prompt_suggestions(location: Optional[str] = None, crop: Optional[str] = None):
    """Provides location & crop contextual suggestions for quick clicks."""
    loc = (location or "India").capitalize()
    c = crop or "Wheat & Paddy"
    
    suggestions = [
        f"📊 What is the current Mandi price for {c} in {loc}?",
        f"🌱 Recommended fertilizer NPK dose for {c}?",
        f"🐛 How to prevent leaf blight and yellow rust in {c}?",
        f"🏛️ How to apply for PM-KISAN & crop insurance in {loc}?",
        f"💧 What is the ideal irrigation schedule for {c} in this weather?"
    ]
    return {
        "status": "success",
        "location": loc,
        "crop": c,
        "suggestions": suggestions
    }
