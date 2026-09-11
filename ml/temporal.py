import os
import csv
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.utils.data import Dataset, DataLoader

TREND_LABELS = {
    0: "STABLE",
    1: "IMPROVING",
    2: "DETERIORATING",
    3: "RAPID_DETERIORATION"
}

TREND_TO_ID = {v: k for k, v in TREND_LABELS.items()}

class RealTemporalDataset(Dataset):
    """
    REAL_TEMPORAL_DATASET Interface: Loads real chronological telemetry sequences from disk / CSV manifest.
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

        grouped = {}
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seq_id = row.get("sequence_id", "default_seq")
                if seq_id not in grouped:
                    grouped[seq_id] = []
                
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
    SYNTHETIC_DEVELOPMENT_TEMPORAL_DATASET Interface: Development sequence dataset.
    Explicitly labeled as synthetic_development with real_world_validation = False.
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


def generate_synthetic_temporal_data(num_samples=1000, seq_len=10, seed=42):
    """
    Generates deterministic physical progression trajectories for SIL simulation mode.
    NO RANDOM LABELS OR DISCONNECTED RANDOM INTEGERS ARE USED.
    Trajectories:
    - HEALTHY (STABLE, trend=0)
    - WATER_STRESS (DETERIORATING, trend=2, temp rises, moisture drops, NIR decays)
    - DISEASE_PROGRESS (RAPID_DETERIORATION, trend=3, high humidity, chlorophyll & Red Edge decay)
    - RECOVERY (IMPROVING, trend=1, moisture increases, spectral health recovers)
    """
    np.random.seed(seed)
    X_seq = []
    trends = []
    fut_sevs = []

    samples_per_trajectory = num_samples // 4

    # Trajectory 0: HEALTHY (STABLE)
    for _ in range(samples_per_trajectory):
        seq = []
        base_moisture = np.random.normal(55.0, 3.0)
        base_temp = np.random.normal(23.0, 1.5)
        for t in range(seq_len):
            temp = base_temp + np.random.normal(0, 0.5)
            hum = np.random.normal(65.0, 2.0)
            soil = max(40.0, base_moisture + np.random.normal(0, 1.0))
            gas = np.random.normal(80.0, 5.0)
            sev = float(np.random.uniform(5.0, 15.0))

            # Healthy spectral reflectance (High NIR 850nm, high Red-Edge 730nm)
            spec = np.array([0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]) + np.random.normal(0, 0.02, 10)
            spec = np.clip(spec, 0.05, 1.0)

            env = [temp / 50.0, hum / 100.0, soil / 100.0, gas / 500.0]
            feat = list(spec) + env + [sev / 100.0]
            seq.append(feat)

        X_seq.append(seq)
        trends.append(0) # STABLE
        fut_sevs.append(seq[-1][-1] * 100.0)

    # Trajectory 1: WATER_STRESS (DETERIORATING)
    for _ in range(samples_per_trajectory):
        seq = []
        start_moisture = np.random.normal(50.0, 4.0)
        start_temp = np.random.normal(25.0, 2.0)
        for t in range(seq_len):
            # Progressive soil moisture drop & temperature rise
            soil = max(10.0, start_moisture - (t * 3.5) + np.random.normal(0, 1.0))
            temp = start_temp + (t * 1.2) + np.random.normal(0, 0.5)
            hum = max(20.0, 60.0 - (t * 2.5) + np.random.normal(0, 1.0))
            gas = np.random.normal(90.0, 8.0)
            sev = min(90.0, 20.0 + (t * 6.0) + np.random.normal(0, 1.5))

            # NIR (band 10) & Red Edge (band 9) decay as water stress progresses
            decay = (t / float(seq_len)) * 0.35
            spec = np.array([0.18, 0.22, 0.25, 0.30, 0.45, 0.55, 0.50, 0.45, 0.60 - decay, 0.85 - decay]) + np.random.normal(0, 0.02, 10)
            spec = np.clip(spec, 0.05, 1.0)

            env = [temp / 50.0, hum / 100.0, soil / 100.0, gas / 500.0]
            feat = list(spec) + env + [sev / 100.0]
            seq.append(feat)

        X_seq.append(seq)
        trends.append(2) # DETERIORATING
        fut_sevs.append(seq[-1][-1] * 100.0)

    # Trajectory 2: DISEASE_PROGRESS (RAPID_DETERIORATION)
    for _ in range(samples_per_trajectory):
        seq = []
        start_sev = np.random.normal(25.0, 3.0)
        for t in range(seq_len):
            temp = np.random.normal(26.0, 1.0)
            hum = min(95.0, 82.0 + (t * 1.0) + np.random.normal(0, 1.0))
            soil = np.random.normal(48.0, 3.0)
            gas = np.random.normal(120.0 + (t * 15.0), 10.0)
            sev = min(100.0, start_sev + (t * 8.0) + np.random.normal(0, 2.0))

            # Chlorophyll absorption (band 8: 680nm) drops dramatically as pathogen spreads
            spec = np.array([0.22, 0.25, 0.28, 0.28, 0.38, 0.50, 0.58, 0.52 - (t*0.03), 0.45 - (t*0.025), 0.40 - (t*0.02)]) + np.random.normal(0, 0.02, 10)
            spec = np.clip(spec, 0.05, 1.0)

            env = [temp / 50.0, hum / 100.0, soil / 100.0, gas / 500.0]
            feat = list(spec) + env + [sev / 100.0]
            seq.append(feat)

        X_seq.append(seq)
        trends.append(3) # RAPID_DETERIORATION
        fut_sevs.append(seq[-1][-1] * 100.0)

    # Trajectory 3: RECOVERY (IMPROVING)
    for _ in range(samples_per_trajectory):
        seq = []
        start_sev = np.random.normal(65.0, 4.0)
        for t in range(seq_len):
            soil = min(60.0, 25.0 + (t * 4.0) + np.random.normal(0, 1.0))
            temp = max(22.0, 32.0 - (t * 1.0) + np.random.normal(0, 0.5))
            hum = np.random.normal(60.0, 3.0)
            gas = np.random.normal(80.0, 5.0)
            sev = max(10.0, start_sev - (t * 5.5) + np.random.normal(0, 1.5))

            # NIR & Red Edge recovery as irrigation replenishes crop vigor
            recovery = (t / float(seq_len)) * 0.30
            spec = np.array([0.16, 0.19, 0.22, 0.33, 0.55 + recovery, 0.42, 0.30, 0.20, 0.55 + recovery, 0.65 + recovery]) + np.random.normal(0, 0.02, 10)
            spec = np.clip(spec, 0.05, 1.0)

            env = [temp / 50.0, hum / 100.0, soil / 100.0, gas / 500.0]
            feat = list(spec) + env + [sev / 100.0]
            seq.append(feat)

        X_seq.append(seq)
        trends.append(1) # IMPROVING
        fut_sevs.append(seq[-1][-1] * 100.0)

    return (
        np.array(X_seq, dtype=np.float32),
        np.array(trends, dtype=np.int64),
        np.array(fut_sevs, dtype=np.float32)
    )


class TemporalStressNet(nn.Module):
    """
    LSTM/GRU Sequential Model for Microclimate & Spectral Trajectory Prediction.
    """
    def __init__(self, in_features=15, hidden_dim=64, num_layers=2, num_classes=4):
        super().__init__()
        self.lstm = nn.LSTM(in_features, hidden_dim, num_layers, batch_first=True, dropout=0.1)
        self.trend_head = nn.Linear(hidden_dim, num_classes)
        self.fut_sev_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

    def forward(self, x_seq):
        # x_seq: (B, T, 15)
        lstm_out, (h_n, c_n) = self.lstm(x_seq)
        last_hidden = lstm_out[:, -1, :] # (B, hidden_dim)

        trend_logits = self.trend_head(last_hidden)
        fut_severity = self.fut_sev_head(last_hidden) * 100.0

        return {
            "trend_logits": trend_logits,
            "future_severity": fut_severity.squeeze(-1),
            "sequence_embeddings": last_hidden
        }


def train_temporal_model(epochs=5, batch_size=32, lr=1e-3, seed=42):
    """
    Trains TemporalStressNet on physical synthetic progression trajectories.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    X_seq, trends, fut_sevs = generate_synthetic_temporal_data(num_samples=1200, seed=seed)

    total = len(trends)
    train_size = int(total * 0.8)

    train_ds = SyntheticTemporalDataset(X_seq[:train_size], trends[:train_size], fut_sevs[:train_size])
    val_ds = SyntheticTemporalDataset(X_seq[train_size:], trends[train_size:], fut_sevs[train_size:])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    model = TemporalStressNet().to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    cls_criterion = nn.CrossEntropyLoss()
    sev_criterion = nn.MSELoss()

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            x_seq = batch["x_seq"].to(device)
            target_trend = batch["trend"].to(device)
            target_sev = batch["future_severity"].to(device)

            optimizer.zero_grad()
            out = model(x_seq)

            l_cls = cls_criterion(out["trend_logits"], target_trend)
            l_sev = sev_criterion(out["future_severity"], target_sev)
            loss = l_cls + 0.01 * l_sev

            loss.backward()
            optimizer.step()
            total_loss += loss.item()

    ckpt_dir = os.path.join(os.path.dirname(__file__), "checkpoints")
    os.makedirs(ckpt_dir, exist_ok=True)
    ckpt_path = os.path.join(ckpt_dir, "temporal_net.pth")

    torch.save({
        "model_state_dict": model.state_dict(),
        "dataset_type": "synthetic_development",
        "real_world_validation": False,
        "epochs": epochs,
        "seed": seed
    }, ckpt_path)

    print(f"[TemporalModel] Successfully trained & saved TemporalStressNet checkpoint to {ckpt_path}")
    return model

if __name__ == "__main__":
    train_temporal_model()
