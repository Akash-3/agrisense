import os
import hashlib
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import (
    register_farmer, login_farmer, check_farmer_exists,
    clear_failed_attempts, execute_db,
    update_farmer_profile, reset_password_direct
)
from dependencies import get_current_user
from models.schemas import (
    RegisterRequest, LoginRequest, SSORequest,
    ResetPasswordRequest, UpdateProfileRequest
)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "agrisense_jwt_enterprise_secret_2026_key_#9821!")

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/register")
async def handle_register(req: RegisterRequest):
    res = register_farmer(
        req.full_name, req.phone_or_email, req.farm_name, req.farm_acres,
        req.password, req.gender, req.age, req.avatar_id, req.crop_type
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.post("/login")
async def handle_login(req: LoginRequest):
    res = login_farmer(req.phone_or_email, req.password)
    if res.get("status") == "error":
        raise HTTPException(status_code=401, detail=res.get("message"))
    return res

@router.post("/demo")
async def handle_demo_login():
    raise HTTPException(status_code=403, detail="Demo login is disabled for security reasons.")

@router.post("/sso/{provider}")
async def handle_sso_login(provider: str, payload: Optional[SSORequest] = None):
    raise HTTPException(status_code=403, detail="SSO login is explicitly disabled.")

@router.post("/forgot-password/reset")
async def handle_forgot_password_reset(req: ResetPasswordRequest):
    res = reset_password_direct(req.phone_or_email, req.new_password)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.post("/profile/update")
async def handle_update_profile(req: UpdateProfileRequest, current_user: int = Depends(get_current_user)):
    return update_farmer_profile(
        farmer_id=current_user,
        full_name=req.full_name,
        phone_or_email=req.phone_or_email,
        phone=req.phone,
        country=req.country,
        country_code=req.country_code,
        address=req.address,
        city=req.city,
        state=req.state,
        postal_code=req.postal_code,
        farm_name=req.farm_name,
        farm_acres=req.farm_acres,
        crop_type=req.crop_type,
        new_password=req.new_password,
        gender=req.gender,
        age=req.age,
        avatar_id=req.avatar_id,
        location=req.location
    )

@router.post("/logout")
async def handle_logout(current_user: int = Depends(get_current_user)):
    execute_db("DELETE FROM auth_sessions WHERE farmer_id = ?", (current_user,), commit=True)
    return {"status": "success", "message": "Logged out successfully"}
