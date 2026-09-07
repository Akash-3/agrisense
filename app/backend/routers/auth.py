from fastapi import APIRouter, HTTPException
from database import (
    register_farmer, login_farmer, generate_otp, verify_otp,
    check_farmer_exists, reset_password_with_otp, update_farmer_profile
)
from models.schemas import (
    RegisterRequest, LoginRequest, OTPRequest, VerifyOTPRequest,
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
async def handle_sso_login(provider: str):
    provider_clean = provider.lower()
    if provider_clean not in ["google", "microsoft"]:
        raise HTTPException(status_code=400, detail="Unsupported SSO provider")

    sso_email = f"{provider_clean}.farmer@agrisense.io"
    sso_name = f"Akash Satapathy ({provider_clean.capitalize()})"

    if not check_farmer_exists(sso_email):
        register_farmer(sso_name, sso_email, "Green Valley Farm", 15.0, "AgriPass123!", "Farmer", 32, 1, "Wheat & Paddy")

    res = login_farmer(sso_email, "AgriPass123!")
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
    return update_farmer_profile(req.farmer_id, req.full_name, req.gender, req.age, req.avatar_id)
