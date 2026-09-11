import base64
import io
from datetime import datetime
import numpy as np
from PIL import Image
from fastapi import APIRouter, HTTPException
from models.schemas import CropImageDiagnosisRequest
from app.backend.services import ai_service, xai_service

router = APIRouter(prefix="/api/v1/ai", tags=["AI Diagnosis"])

@router.post("/diagnose-crop-image")
async def diagnose_crop_image(payload: CropImageDiagnosisRequest):
    crop = payload.crop_type or "Wheat & Paddy"
    note = payload.note or ""
    image_raw = payload.image_base64 or ""

    # REAL COMPUTER VISION INFERENCE ON UPLOADED IMAGE
    if image_raw:
        try:
            # Strip base64 header if present
            if "," in image_raw:
                image_raw = image_raw.split(",")[1]
            img_bytes = base64.b64decode(image_raw)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB").resize((64, 64))
            spat_arr = np.array(img, dtype=np.float32).transpose(2, 0, 1) / 255.0

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
