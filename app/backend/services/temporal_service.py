import os
import torch
import numpy as np
from ml.temporal import TemporalStressNet, TREND_LABELS

CHECKPOINT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "checkpoints", "temporal_net.pth"))

class TemporalService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = TemporalStressNet(in_features=15, hidden_dim=64, num_classes=4).to(self.device)
        self.loaded = False
        self._load_checkpoint()

    def _load_checkpoint(self):
        if os.path.exists(CHECKPOINT_PATH):
            try:
                ckpt = torch.load(CHECKPOINT_PATH, map_location=self.device)
                self.model.load_state_dict(ckpt["model_state_dict"])
                self.model.eval()
                self.loaded = True
                print(f"[TemporalService] Loaded TemporalStressNet checkpoint from {CHECKPOINT_PATH}")
            except Exception as e:
                print(f"[TemporalService] Warning: Could not load temporal checkpoint ({e}).")

    def evaluate_trend(self, historical_sequence):
        """
        Evaluates historical sequence (list of feature vectors) to predict stress progression trend.
        - historical_sequence: list of length T (e.g. 5 to 10), each having 15 features.
        """
        self.model.eval()
        seq_len = len(historical_sequence)
        if seq_len == 0:
            return {
                "trend": "STABLE",
                "trend_confidence": 1.0,
                "projected_future_severity": 0.0,
                "timesteps_analyzed": 0
            }

        # Pad/truncate sequence to 10 timesteps if necessary
        if seq_len < 10:
            padding = [historical_sequence[0]] * (10 - seq_len)
            seq_arr = np.array(padding + historical_sequence, dtype=np.float32)
        else:
            seq_arr = np.array(historical_sequence[-10:], dtype=np.float32)

        # Pad vector length to 15 features if needed
        if seq_arr.shape[1] < 15:
            pad_cols = np.zeros((10, 15 - seq_arr.shape[1]), dtype=np.float32)
            seq_arr = np.hstack([seq_arr, pad_cols])
        elif seq_arr.shape[1] > 15:
            seq_arr = seq_arr[:, :15]

        seq_tensor = torch.tensor([seq_arr], dtype=torch.float32).to(self.device)

        with torch.no_grad():
            out = self.model(seq_tensor)
            logits = out["trend_logits"][0]
            probs = torch.softmax(logits, dim=0).cpu().numpy()
            pred_id = int(torch.argmax(logits).item())
            fut_sev = float(out["future_severity"][0].item())

        trend_name = TREND_LABELS.get(pred_id, "STABLE")

        return {
            "trend": trend_name,
            "trend_confidence": round(float(probs[pred_id]), 4),
            "projected_future_severity": round(fut_sev, 2),
            "timesteps_analyzed": seq_len,
            "model_type": "GRU-TemporalStressNet"
        }

temporal_service = TemporalService()
