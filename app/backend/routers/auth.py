import hashlib
from typing import Optional
from fastapi import APIRouter, HTTPException
from database import (
    register_farmer, login_farmer, generate_otp, verify_otp,
    check_farmer_exists, reset_password_with_otp, update_farmer_profile
)
from models.schemas import (
    RegisterRequest, LoginRequest, SSORequest, OTPRequest, VerifyOTPRequest,
    ResetPasswordRequest, UpdateProfileRequest
)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/send-otp")
async def handle_send_otp(req: OTPRequest):
    if check_farmer_exists(req.phone_or_email):
        raise HTTPException(
            status_code=400,
            detail=f"Account Already Exists: '{req.phone_or_email}' is already registered! Please switch to the Login tab to sign in."
        )
    otp = generate_otp(req.phone_or_email, full_name=req.full_name)
    return {
        "status": "success",
        "message": f"Verification OTP code generated and sent to {req.phone_or_email}!",
        "demo_otp": otp
    }

@router.post("/verify-otp")
async def handle_verify_otp(req: VerifyOTPRequest):
    if verify_otp(req.phone_or_email, req.otp_code):
        return {"status": "success", "message": "OTP verified successfully!"}
    raise HTTPException(status_code=400, detail="Invalid or expired OTP code")

@router.post("/register")
async def handle_register(req: RegisterRequest):
    res = register_farmer(req.full_name, req.phone_or_email, req.farm_name, req.farm_acres, req.password, req.gender, req.age, req.avatar_id, req.crop_type)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.post("/login")
async def handle_login(req: LoginRequest):
    res = login_farmer(req.phone_or_email, req.password)
    if res.get("status") == "error":
        raise HTTPException(status_code=401, detail=res.get("message"))
    return res

@router.post("/sso/{provider}")
async def handle_sso_login(provider: str, payload: Optional[SSORequest] = None):
    provider_clean = provider.lower()
    if provider_clean not in ["google", "microsoft"]:
        raise HTTPException(status_code=400, detail="Unsupported SSO provider")

    sso_name = (payload.full_name if payload and payload.full_name else f"{provider_clean.capitalize()} Farmer")
    sso_email = (payload.email if payload and payload.email else f"{provider_clean}.farmer@agrisense.io")
    avatar_id = (payload.avatar_id if payload and payload.avatar_id else 1)
    farm_name = (payload.farm_name if payload and payload.farm_name else f"{sso_name}'s Farm")
    farm_acres = (payload.farm_acres if payload and payload.farm_acres is not None else 10.0)
    crop_type = (payload.crop_type if payload and payload.crop_type else "Wheat & Paddy")
    gender = (payload.gender if payload and payload.gender else "Farmer")
    age = (payload.age if payload and payload.age is not None else 30)

    sso_internal_pass = f"SSO_SECURE_{hashlib.sha256(sso_email.encode()).hexdigest()[:16]}"

    if not check_farmer_exists(sso_email):
        register_farmer(sso_name, sso_email, farm_name, farm_acres, sso_internal_pass, gender, age, avatar_id, crop_type)

    res = login_farmer(sso_email, sso_internal_pass)
    return {
        "status": "success",
        "provider": provider_clean,
        "message": f"Successfully authenticated via {provider_clean.capitalize()} SSO!",
        "farmer": res.get("farmer")
    }

@router.post("/forgot-password/send-otp")
async def handle_forgot_password_send_otp(req: OTPRequest):
    if not check_farmer_exists(req.phone_or_email):
        raise HTTPException(
            status_code=404,
            detail=f"No account registered with '{req.phone_or_email}'. Please check your email or register."
        )
    otp = generate_otp(req.phone_or_email, full_name=req.full_name)
    return {
        "status": "success",
        "message": f"Password reset OTP sent to {req.phone_or_email}!",
        "demo_otp": otp
    }

@router.post("/forgot-password/reset")
async def handle_forgot_password_reset(req: ResetPasswordRequest):
    res = reset_password_with_otp(req.phone_or_email, req.new_password, req.otp_code)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.post("/profile/update")
async def handle_update_profile(req: UpdateProfileRequest):
    return update_farmer_profile(
        farmer_id=req.farmer_id,
        full_name=req.full_name,
        phone_or_email=req.phone_or_email,
        farm_name=req.farm_name,
        farm_acres=req.farm_acres,
        crop_type=req.crop_type,
        new_password=req.new_password,
        gender=req.gender,
        age=req.age,
        avatar_id=req.avatar_id,
        location=req.location
    )
