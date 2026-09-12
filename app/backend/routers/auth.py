import hashlib
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from dependencies import get_current_user
from database import (
    register_farmer, login_farmer, generate_otp, verify_otp,
    check_farmer_exists, reset_password_with_otp, update_farmer_profile,
    clear_failed_attempts, hash_password, generate_salt, execute_db
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
    generate_otp(req.phone_or_email, full_name=req.full_name)
    return {
        "status": "success",
        "message": f"Verification OTP code generated and sent to {req.phone_or_email}!"
    }

@router.post("/verify-otp")
async def handle_verify_otp(req: VerifyOTPRequest):
    if verify_otp(req.phone_or_email, req.otp_code):
        return {"status": "success", "message": "OTP verified successfully!"}
    raise HTTPException(status_code=400, detail="Invalid or expired OTP code")

@router.post("/register")
async def handle_register(req: RegisterRequest):
    if not verify_otp(req.phone_or_email, req.otp_code):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code")
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

@router.post("/demo")
async def handle_demo_login():
    demo_email = "demo.farmer@agrisense.io"
    demo_name = "Alex Vance"
    demo_farm = "Green Valley Field Plot"
    demo_acres = 15.0
    demo_crop = "Wheat & Paddy"
    demo_pass = "Demo@Pass2026!"

    clear_failed_attempts(demo_email)

    if not check_farmer_exists(demo_email):
        register_farmer(demo_name, demo_email, demo_farm, demo_acres, demo_pass, "Farmer", 32, 1, demo_crop)
    else:
        salt = generate_salt()
        pwd_hash = hash_password(demo_pass, salt)
        execute_db("UPDATE farmers SET password_hash = ?, salt = ? WHERE LOWER(phone_or_email) = ?", (pwd_hash, salt, demo_email), commit=True)

    res = login_farmer(demo_email, demo_pass)
    return {
        "status": "success",
        "demo_mode": True,
        "message": "Authenticated into AgriSense Demo Account!",
        "farmer": res.get("farmer") or {
            "id": 1,
            "full_name": demo_name,
            "phone_or_email": demo_email,
            "farm_name": demo_farm,
            "farm_acres": demo_acres,
            "crop_type": demo_crop
        }
    }

@router.post("/sso/{provider}")
async def handle_sso_login(provider: str, payload: Optional[SSORequest] = None):
    provider_clean = provider.lower()
    if provider_clean not in ["google", "microsoft"]:
        raise HTTPException(status_code=400, detail="Unsupported SSO provider")

    if payload and payload.email and payload.email.strip():
        sso_email = payload.email.strip().lower()
    else:
        sso_email = f"{provider_clean}.farmer@agrisense.io"

    if payload and payload.full_name and payload.full_name.strip():
        sso_name = payload.full_name.strip()
    elif "@" in sso_email:
        name_part = sso_email.split("@")[0].replace(".", " ").replace("_", " ").title()
        sso_name = name_part if name_part else f"{provider_clean.capitalize()} Farmer"
    else:
        sso_name = f"{provider_clean.capitalize()} Farmer"

    avatar_id = (payload.avatar_id if payload and payload.avatar_id else 1)
    farm_name = (payload.farm_name if payload and payload.farm_name else f"{sso_name}'s Farm")
    farm_acres = (payload.farm_acres if payload and payload.farm_acres is not None else 10.0)
    crop_type = (payload.crop_type if payload and payload.crop_type else "Wheat & Paddy")
    gender = (payload.gender if payload and payload.gender else "Farmer")
    age = (payload.age if payload and payload.age is not None else 30)

    clear_failed_attempts(sso_email)
    sso_internal_pass = f"SSO_SECURE_{hashlib.sha256(sso_email.encode()).hexdigest()[:16]}!92"

    if not check_farmer_exists(sso_email):
        register_farmer(sso_name, sso_email, farm_name, farm_acres, sso_internal_pass, gender, age, avatar_id, crop_type)
    else:
        salt = generate_salt()
        pwd_hash = hash_password(sso_internal_pass, salt)
        execute_db("UPDATE farmers SET password_hash = ?, salt = ? WHERE LOWER(phone_or_email) = ?", (pwd_hash, salt, sso_email), commit=True)

    res = login_farmer(sso_email, sso_internal_pass)
    return {
        "status": "success",
        "provider": provider_clean,
        "message": f"Successfully authenticated as {sso_email} via {provider_clean.capitalize()} SSO!",
        "farmer": res.get("farmer") or {
            "id": 1,
            "full_name": sso_name,
            "phone_or_email": sso_email,
            "phone": "+1 (555) 019-2834",
            "farm_name": farm_name,
            "farm_acres": farm_acres,
            "crop_type": crop_type
        }
    }

@router.post("/forgot-password/send-otp")
async def handle_forgot_password_send_otp(req: OTPRequest):
    if not check_farmer_exists(req.phone_or_email):
        raise HTTPException(
            status_code=404,
            detail=f"No account registered with '{req.phone_or_email}'. Please check your email or register."
        )
    generate_otp(req.phone_or_email, full_name=req.full_name)
    return {
        "status": "success",
        "message": f"Password reset OTP sent to {req.phone_or_email}!"
    }

@router.post("/forgot-password/reset")
async def handle_forgot_password_reset(req: ResetPasswordRequest):
    res = reset_password_with_otp(req.phone_or_email, req.new_password, req.otp_code)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.post("/password-change/send-otp")
async def handle_password_change_send_otp(req: OTPRequest):
    if not check_farmer_exists(req.phone_or_email):
        raise HTTPException(
            status_code=404,
            detail=f"Account not found for '{req.phone_or_email}'."
        )
    generate_otp(req.phone_or_email, full_name=req.full_name)
    return {
        "status": "success",
        "message": f"Password change OTP verification code sent to {req.phone_or_email}!"
    }

@router.post("/password-change/reset")
async def handle_password_change_reset(req: ResetPasswordRequest):
    res = reset_password_with_otp(req.phone_or_email, req.new_password, req.otp_code)
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
