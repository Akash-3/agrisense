import os
import torch
import numpy as np
from ml.model import MMSSNet
from ml.dataset import CONDITION_LABELS

CHECKPOINT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "checkpoints", "mmssnet.pth"))

class AIService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = MMSSNet(num_classes=6).to(self.device)
        self.loaded = False
        self._load_checkpoint()

    def _load_checkpoint(self):
        if os.path.exists(CHECKPOINT_PATH):
            try:
                ckpt = torch.load(CHECKPOINT_PATH, map_location=self.device)
                self.model.load_state_dict(ckpt["model_state_dict"])
                self.model.eval()
                self.loaded = True
                print(f"[AIService] Successfully loaded MM-SSNet checkpoint from {CHECKPOINT_PATH}")
            except Exception as e:
                print(f"[AIService] Warning: Could not load checkpoint ({e}). Using untrained model.")
        else:
            print(f"[AIService] Warning: Checkpoint not found at {CHECKPOINT_PATH}. Using default model.")

    def predict(self, spectral, env, spatial=None):
        """
        Runs MM-SSNet inference on spectral, environmental, and optional spatial inputs.
        When spatial is None, routes to reduced-modality inference and sets spatial_modality_available: false.
        DO NOT manufacture fake green RGB images.
        """
        self.model.eval()

        spec_tensor = torch.tensor([spectral], dtype=torch.float32).to(self.device)
        
        # Format env: [temp/50, hum/100, soil/100, gas/500]
        env_norm = [
            env[0] / 50.0 if env[0] > 1.0 else env[0],
            env[1] / 100.0 if env[1] > 1.0 else env[1],
            env[2] / 100.0 if env[2] > 1.0 else env[2],
            env[3] / 500.0 if env[3] > 1.0 else env[3]
        ]
        env_tensor = torch.tensor([env_norm], dtype=torch.float32).to(self.device)

        if spatial is None:
            spat_tensor = None
        else:
            spat_arr = np.array(spatial, dtype=np.float32)
            if spat_arr.size == 0 or np.abs(spat_arr).sum() < 1e-4:
                spat_tensor = None
            else:
                spat_tensor = torch.tensor([spat_arr], dtype=torch.float32).to(self.device)

        with torch.no_grad():
            out = self.model(spec_tensor, spat_tensor, env_tensor)
            logits = out["class_logits"][0]
            probs = torch.softmax(logits, dim=0).cpu().numpy().tolist()
            pred_class_id = int(torch.argmax(logits).item())
            severity = float(out["severity"][0].item())
            lead_time = float(out["lead_time"][0].item())
            
            attn_weights = out["attn_weights"][0].cpu().numpy().tolist() if "attn_weights" in out and out["attn_weights"] is not None else []
            latent_features = out["latent_features"][0].cpu().numpy().tolist()
            spat_avail = bool(out.get("spatial_modality_available", False))

        condition_name = CONDITION_LABELS.get(pred_class_id, "UNKNOWN")

        probabilities_dict = {
            CONDITION_LABELS[i]: round(probs[i], 4) for i in range(len(probs))
        }

        return {
            "condition": condition_name,
            "condition_id": pred_class_id,
            "confidence": round(probs[pred_class_id], 4),
            "severity_score": round(severity, 2),
            "estimated_lead_time_hours": round(lead_time, 1),
            "probabilities": probabilities_dict,
            "attention_weights": attn_weights,
            "latent_features": latent_features,
            "spatial_modality_available": spat_avail,
            "model_name": "MM-SSNet",
            "model_version": "0.2.0",
            "dataset_type": "synthetic_development",
            "real_world_validation": False
        }

ai_service = AIService()
