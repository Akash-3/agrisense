import torch
import torch.nn.functional as F
import numpy as np
from app.backend.services.ai_service import ai_service

class XAIService:
    """
    Explainable AI (XAI) Engine using PyTorch Grad-CAM & Input x Gradient attributions.
    NO FIXED GAUSSIAN HEATMAPS OR HARDCODED WEIGHTS ARE USED.
    If RGB spatial image is missing, Grad-CAM is marked UNAVAILABLE_MISSING_RGB.
    """

    def generate_xai_explanation(self, spectral_data, spatial_img=None, target_class_id=None):
        """
        Generates real Grad-CAM heatmap matrix (if spatial_img provided) and Input x Gradient spectral band attributions.
        - spectral_data: list of 10 AS7341 band values
        - spatial_img: optional (3, 64, 64) numpy array or None
        """
        model = ai_service.model
        device = ai_service.device
        model.eval()

        spec_arr = np.array(spectral_data if len(spectral_data) == 10 else [0.2]*10, dtype=np.float32)
        spec_tensor = torch.tensor([spec_arr], dtype=torch.float32, device=device).requires_grad_(True)
        env_tensor = torch.tensor([[0.5, 0.6, 0.5, 0.2]], dtype=torch.float32, device=device)

        has_spatial = False
        if spatial_img is not None:
            spat_arr = np.array(spatial_img, dtype=np.float32)
            if spat_arr.size > 0 and np.abs(spat_arr).sum() > 1e-4:
                has_spatial = True
                if spat_arr.ndim == 3 and spat_arr.shape[0] != 3:
                    spat_arr = spat_arr.transpose(2, 0, 1)

        # ---------------- 1. REAL GRAD-CAM FOR MOBILENETV3 (IF SPATIAL AVAILABLE) ----------------
        heatmap_normalized = None
        xai_status = "UNAVAILABLE_MISSING_RGB"

        if has_spatial:
            spat_tensor = torch.tensor([spat_arr], dtype=torch.float32, device=device).requires_grad_(True)
            activations = []
            gradients = []

            def forward_hook(module, input, output):
                activations.append(output)

            def backward_hook(module, grad_in, grad_out):
                gradients.append(grad_out[0])

            target_layer = model.spatial_stream.backbone.features[-1]
            h_fw = target_layer.register_forward_hook(forward_hook)
            h_bw = target_layer.register_full_backward_hook(backward_hook)

            model.zero_grad()
            out = model(spec_tensor, spat_tensor, env_tensor)
            logits = out["class_logits"][0]

            if target_class_id is None:
                target_class_id = int(torch.argmax(logits).item())

            target_score = logits[target_class_id]

            # Compute spectral gradients using autograd.grad
            spec_grads = torch.autograd.grad(target_score, spec_tensor, retain_graph=True, allow_unused=True)[0]
            target_score.backward(retain_graph=True)

            h_fw.remove()
            h_bw.remove()

            if activations and gradients:
                act = activations[0].detach()
                grad = gradients[0].detach()

                weights = torch.mean(grad, dim=(2, 3), keepdim=True)
                cam = torch.sum(weights * act, dim=1, keepdim=True)
                cam = F.relu(cam)

                cam_resized = F.interpolate(cam, size=(64, 64), mode="bilinear", align_corners=False)
                cam_arr = cam_resized[0, 0].cpu().numpy()
                
                c_min, c_max = cam_arr.min(), cam_arr.max()
                if c_max > c_min:
                    heatmap_normalized = ((cam_arr - c_min) / (c_max - c_min)).round(3).tolist()
                else:
                    heatmap_normalized = np.zeros((64, 64), dtype=np.float32).tolist()
                xai_status = "AVAILABLE"
            else:
                heatmap_normalized = None
        else:
            # Spatial missing: forward pass without spatial for spectral gradients
            model.zero_grad()
            out = model(spec_tensor, None, env_tensor)
            logits = out["class_logits"][0]
            if target_class_id is None:
                target_class_id = int(torch.argmax(logits).item())
            target_score = logits[target_class_id]
            spec_grads = torch.autograd.grad(target_score, spec_tensor, retain_graph=True, allow_unused=True)[0]

        # ---------------- 2. REAL INPUT x GRADIENT SPECTRAL ATTRIBUTION ----------------
        if spec_grads is not None:
            spec_g = spec_grads[0].cpu().numpy()
        else:
            spec_g = np.zeros(10)

        attr_scores = np.abs(spec_arr * spec_g)
        total_attr = attr_scores.sum()
        if total_attr > 0:
            importance_pcts = (attr_scores / total_attr) * 100.0
        else:
            importance_pcts = np.full(10, 10.0)

        wavelengths = [
            {"band": "F1 (415nm - Violet)", "nm": 415},
            {"band": "F2 (445nm - Blue)", "nm": 445},
            {"band": "F3 (480nm - Cyan)", "nm": 480},
            {"band": "F4 (515nm - Green)", "nm": 515},
            {"band": "F5 (555nm - Yellow-Green)", "nm": 555},
            {"band": "F6 (590nm - Yellow)", "nm": 590},
            {"band": "F7 (630nm - Orange)", "nm": 630},
            {"band": "F8 (680nm - Red/Chlorophyll)", "nm": 680},
            {"band": "Clear (730nm - Red Edge)", "nm": 730},
            {"band": "NIR (850nm - Near Infrared)", "nm": 850}
        ]

        band_importance = []
        for idx, item in enumerate(wavelengths):
            band_importance.append({
                "band_name": item["band"],
                "wavelength_nm": item["nm"],
                "reflectance_value": round(float(spec_arr[idx]), 4),
                "attribution_weight": round(float(attr_scores[idx]), 6),
                "importance_pct": round(float(importance_pcts[idx]), 1)
            })

        top_band = max(band_importance, key=lambda x: x["importance_pct"])["band_name"]

        return {
            "xai_status": xai_status,
            "spatial_modality_available": has_spatial,
            "spectral_band_importance": band_importance,
            "gradcam_heatmap_grid": heatmap_normalized,
            "top_attributing_band": top_band,
            "xai_method": "PyTorch Grad-CAM (MobileNetV3) + Input × Gradient",
            "target_class_id": target_class_id,
            "dataset_type": "synthetic_development",
            "real_world_validation": False
        }

xai_service = XAIService()
