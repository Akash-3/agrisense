import os
import csv
import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import Dataset

TREND_LABELS = {
    0: "STABLE",
    1: "IMPROVING",
    2: "DETERIORATING",
    3: "RAPID_DETERIORATION"
}

TREND_TO_ID = {v: k for k, v in TREND_LABELS.items()}

class RealTemporalDataset(Dataset):
    """
    REAL_TEMPORAL_DATASET Interface: Loads real chronological telemetry sequences from database or CSV manifest.
    Each item is a sequence of length T (e.g. 10 timesteps) of 15 features:
    [10 spectral channels, 4 environmental metrics, 1 previous severity score].
    """
    DATASET_TYPE = "REAL_TEMPORAL_DATASET"

    def __init__(self, manifest_csv, seq_len=10):
        self.manifest_path = manifest_csv
        self.seq_len = seq_len
        self.sequences = []
        self._load_sequences()

    def _load_sequences(self):
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"[RealTemporalDataset] Manifest CSV not found at: {self.manifest_path}")

        # Group rows by sequence_id
        grouped = {}
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seq_id = row.get("sequence_id", "default_seq")
                if seq_id not in grouped:
                    grouped[seq_id] = []
                
                # 15 features: 10 spectral, 4 env, 1 prev_sev
                spec = [float(row.get(f"f{i+1}", 0.1)) for i in range(10)]
                env = [float(row.get("temp_c", 25.0))/50.0, float(row.get("hum_pct", 60.0))/100.0, float(row.get("soil_moisture_pct", 50.0))/100.0, float(row.get("gas_ppm", 80.0))/500.0]
                prev_sev = float(row.get("prev_severity", 0.0))/100.0

                feat_vec = spec + env + [prev_sev]
                trend_str = row.get("trend_label", "STABLE").strip().upper()
                trend_id = TREND_TO_ID.get(trend_str, 0)
                fut_sev = float(row.get("future_severity", 0.0))

                grouped[seq_id].append({
                    "features": feat_vec,
                    "trend": trend_id,
                    "future_severity": fut_sev
                })

        for seq_id, items in grouped.items():
            if len(items) >= self.seq_len:
                # Take window of seq_len timesteps
                for start in range(0, len(items) - self.seq_len + 1, 2):
                    window = items[start : start + self.seq_len]
                    x_arr = np.array([w["features"] for w in window], dtype=np.float32)
                    last_item = window[-1]
                    self.sequences.append({
                        "x": x_arr,
                        "trend": last_item["trend"],
                        "future_severity": last_item["future_severity"]
                    })

        print(f"[RealTemporalDataset] Loaded {len(self.sequences)} REAL temporal sequences from {self.manifest_path}")

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        s = self.sequences[idx]
        return {
            "x_seq": torch.tensor(s["x"], dtype=torch.float32),
            "trend": torch.tensor(s["trend"], dtype=torch.long),
            "future_severity": torch.tensor(s["future_severity"], dtype=torch.float32),
            "dataset_type": self.DATASET_TYPE
        }


class SyntheticTemporalDataset(Dataset):
    """
    SYNTHETIC_DEVELOPMENT_TEMPORAL_DATASET Interface: Development simulator sequence dataset.
    """
    DATASET_TYPE = "SYNTHETIC_DEVELOPMENT_TEMPORAL_DATASET"

    def __init__(self, x_sequences, trends, future_severities):
        self.x_sequences = torch.tensor(x_sequences, dtype=torch.float32)
        self.trends = torch.tensor(trends, dtype=torch.long)
        self.future_severities = torch.tensor(future_severities, dtype=torch.float32)

    def __len__(self):
        return len(self.trends)

    def __getitem__(self, idx):
        return {
            "x_seq": self.x_sequences[idx],
            "trend": self.trends[idx],
            "future_severity": self.future_severities[idx],
            "dataset_type": self.DATASET_TYPE
        }


def generate_synthetic_temporal_data(num_samples=1000, seq_len=10, in_features=15, seed=42):
    """
    Generates synthetic sequential data explicitly marked for development & SIL simulation.
    """
    np.random.seed(seed)
    X_seq = []
    trends = []
    fut_sevs = []

    for _ in range(num_samples):
        trend_id = np.random.randint(0, 4)
        base_sev = np.random.uniform(10.0, 80.0)
        seq = []

        for t in range(seq_len):
            if trend_id == 0: # STABLE
                sev = base_sev + np.random.normal(0, 1.0)
            elif trend_id == 1: # IMPROVING
                sev = max(0.0, base_sev - t * 2.0 + np.random.normal(0, 1.0))
            elif trend_id == 2: # DETERIORATING
                sev = min(100.0, base_sev + t * 3.0 + np.random.normal(0, 1.0))
            else: # RAPID_DETERIORATION
                sev = min(100.0, base_sev + t * 6.0 + np.random.normal(0, 1.0))

            spec = [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]
            env = [25.0/50.0, 60.0/100.0, 50.0/100.0, 80.0/500.0]
            feat = spec + env + [sev/100.0]
            seq.append(feat)

        X_seq.append(seq)
        trends.append(trend_id)
        fut_sevs.append(seq[-1][-1] * 100.0)

    return (
        np.array(X_seq, dtype=np.float32),
        np.array(trends, dtype=np.int64),
        np.array(fut_sevs, dtype=np.float32)
    )


class TemporalStressNet(nn.Module):
    """
    GRU-based Temporal Sequence Model for crop stress trajectory prediction.
    """
    def __init__(self, in_features=15, hidden_dim=64, num_layers=2, num_classes=4):
        super().__init__()
        self.gru = nn.GRU(
            input_size=in_features,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.1 if num_layers > 1 else 0.0
        )
        self.trend_head = nn.Linear(hidden_dim, num_classes)
        self.future_severity_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

    def forward(self, x_seq):
        out, h_n = self.gru(x_seq)
        last_hidden = out[:, -1, :]
        trend_logits = self.trend_head(last_hidden)
        future_severity = self.future_severity_head(last_hidden) * 100.0

        return {
            "trend_logits": trend_logits,
            "future_severity": future_severity.squeeze(-1)
        }
