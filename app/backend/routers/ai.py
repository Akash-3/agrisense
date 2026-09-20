import base64
import io
from datetime import datetime
import numpy as np
from PIL import Image
from fastapi import APIRouter, HTTPException, Depends
from dependencies import get_current_user
from models.schemas import CropImageDiagnosisRequest
from services import ai_service, xai_service

router = APIRouter(prefix="/api/v1/ai", tags=["AI Diagnosis"])

MAX_IMAGE_PIXELS = 4096 * 4096   # ~16 MP; rejects decompression-bomb images
MAX_DIMENSION    = 4096           # either side

@router.post("/diagnose-crop-image")
async def diagnose_crop_image(payload: CropImageDiagnosisRequest, current_user: int = Depends(get_current_user)):
    crop = payload.crop_type or "Wheat & Paddy"
    note = payload.note or ""
    image_raw = payload.image_base64 or ""

    # REAL COMPUTER VISION INFERENCE ON UPLOADED IMAGE
    if image_raw:
        if len(image_raw) > 7 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Image payload too large (max ~5MB allowed)")

        if "," in image_raw:
            image_raw = image_raw.split(",")[1]
        try:
            img_bytes = base64.b64decode(image_raw)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 payload")

        if len(img_bytes) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Image file too large (max 5MB allowed)")

        try:
            img = Image.open(io.BytesIO(img_bytes))
            img.verify()
            # Re-open after verify() (verify closes the image)
            img = Image.open(io.BytesIO(img_bytes))
            w, h = img.size
            if w > MAX_DIMENSION or h > MAX_DIMENSION:
                raise HTTPException(
                    status_code=413,
                    detail=f"Image dimensions too large (max {MAX_DIMENSION}x{MAX_DIMENSION} px)"
                )
            if w * h > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=413,
                    detail="Image pixel count exceeds safe limit (possible decompression bomb)"
                )
            img = img.convert("RGB").resize((64, 64))
            spat_arr = np.array(img, dtype=np.float32).transpose(2, 0, 1) / 255.0
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=415, detail="Invalid image file or unsupported format")

        try:
            # Default spectral & env for vision-only analysis
            default_spectral = [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]
            default_env = [25.0, 60.0, 50.0, 80.0]

            # Run PyTorch MM-SSNet with MobileNetV3 Backbone
            pred = ai_service.predict(default_spectral, default_env, spatial=spat_arr)
            xai = xai_service.generate_xai_explanation(default_spectral, spat_arr)

            return {
                "status": "success",
                "model_type": "PYTORCH_MMSSNET_MOBILENETV3",
                "crop_type": crop,
                "diagnosis": {
                    "crop_condition": pred["condition"].replace("_", " "),
                    "disease_type": pred["condition"],
                    "confidence_pct": round(pred["confidence"] * 100.0, 1),
                    "severity_score": pred["severity_score"],
                    "estimated_lead_time_hours": pred["estimated_lead_time_hours"],
                    "probabilities": pred["probabilities"],
                    "top_attributing_spectral_band": xai["top_attributing_band"]
                },
                "xai_gradcam_heatmap": xai["gradcam_heatmap_grid"],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process image tensor with PyTorch MobileNetV3: {str(e)}")

    # LEGACY HEURISTIC DEMO PRESETS (EXPLICITLY LABELLED)
    if note in ["Leaf Blight Scan", "Yellow Rust Scan", "Chlorosis Scan", "Healthy Canopy"]:
        if note == "Healthy Canopy":
            cond, sev = "Healthy Canopy", "HEALTHY"
        elif note == "Yellow Rust Scan":
            cond, sev = "Yellow Rust (Stripe Rust)", "HIGH_RISK"
        elif note == "Chlorosis Scan":
            cond, sev = "Nutritional Chlorosis", "MILD_STRESS"
        else:
            cond, sev = "Early Leaf Blight", "MODERATE_RISK"

        return {
            "status": "success",
            "model_type": "LEGACY_HEURISTIC_DEMO",
            "crop_type": crop,
            "diagnosis": {
                "crop_condition": cond,
                "severity": sev,
                "note": "Preserved demo preset. Upload a real crop image to invoke the PyTorch MobileNetV3 MM-SSNet vision pipeline."
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    return {
        "status": "error",
        "message": "No crop image or valid preset provided.",
        "model_type": "PYTORCH_MMSSNET_MOBILENETV3"
    }
