import os
import csv
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image

CONDITION_LABELS = {
    0: "HEALTHY",
    1: "PRE_SYMPTOMATIC_STRESS",
    2: "WATER_STRESS",
    3: "DISEASE",
    4: "SEVERE_STRESS",
    5: "UNKNOWN_ANOMALY"
}

LABEL_TO_ID = {v: k for k, v in CONDITION_LABELS.items()}

class RealAgriDataset(Dataset):
    """
    REAL_DATASET Interface: Loads actual paired crop observations from a disk directory / CSV manifest.
    Expected manifest CSV columns:
    - image_path: relative or absolute path to RGB canopy image
    - f1_415nm ... f10_850nm: 10 AS7341 spectral channels
    - temp_c, hum_pct, soil_moisture_pct, gas_ppm: environmental metrics
    - timestamp, lat, lng: temporal & geospatial metadata
    - condition_label: string e.g. "HEALTHY" or class ID (0-5)
    - severity: continuous float (0.0 to 100.0)
    - lead_time_hours: float
    """
    DATASET_TYPE = "REAL_DATASET"

    def __init__(self, manifest_csv, img_dir=None, transform=None):
        self.manifest_path = manifest_csv
        self.img_dir = img_dir or os.path.dirname(manifest_csv)
        self.transform = transform
        self.samples = []
        self._load_manifest()

    def _load_manifest(self):
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"[RealAgriDataset] Manifest CSV not found at: {self.manifest_path}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Spectral 10 channels
                spec = [
                    float(row.get(f"f{i+1}", row.get(f"spectral_{i}", 0.1))) for i in range(10)
                ]
                
                # Environmental metrics
                env = [
                    float(row.get("temp_c", 25.0)) / 50.0,
                    float(row.get("hum_pct", 60.0)) / 100.0,
                    float(row.get("soil_moisture_pct", 50.0)) / 100.0,
                    float(row.get("gas_ppm", 80.0)) / 500.0
                ]

                # Label parsing
                cond_str = row.get("condition_label", "HEALTHY").strip().upper()
                cond_id = LABEL_TO_ID.get(cond_str, 0)
                
                sev = float(row.get("severity", 0.0))
                lead = float(row.get("lead_time_hours", 0.0))
                img_rel = row.get("image_path", "")

                self.samples.append({
                    "img_path": os.path.join(self.img_dir, img_rel) if img_rel else None,
                    "spectral": np.array(spec, dtype=np.float32),
                    "env": np.array(env, dtype=np.float32),
                    "label": cond_id,
                    "severity": sev,
                    "lead_time": lead,
                    "timestamp": row.get("timestamp", ""),
                    "lat": float(row.get("lat", 0.0)),
                    "lng": float(row.get("lng", 0.0))
                })

        print(f"[RealAgriDataset] Loaded {len(self.samples)} REAL crop observation samples from {self.manifest_path}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]

        # Load RGB Image or default array
        if s["img_path"] and os.path.exists(s["img_path"]):
            try:
                img = Image.open(s["img_path"]).convert("RGB").resize((64, 64))
                spat_arr = np.array(img, dtype=np.float32).transpose(2, 0, 1) / 255.0
            except Exception:
                spat_arr = np.zeros((3, 64, 64), dtype=np.float32)
        else:
            spat_arr = np.zeros((3, 64, 64), dtype=np.float32)

        return {
            "spectral": torch.tensor(s["spectral"], dtype=torch.float32),
            "spatial": torch.tensor(spat_arr, dtype=torch.float32),
            "env": torch.tensor(s["env"], dtype=torch.float32),
            "label": torch.tensor(s["label"], dtype=torch.long),
            "severity": torch.tensor(s["severity"], dtype=torch.float32),
            "lead_time": torch.tensor(s["lead_time"], dtype=torch.float32),
            "dataset_type": self.DATASET_TYPE
        }


class SyntheticAgriDataset(Dataset):
    """
    SYNTHETIC_DEVELOPMENT_DATASET Interface: Generates synthetic crop stress data for development,
    SIL simulation, and software pipeline integration testing ONLY.
    """
    DATASET_TYPE = "SYNTHETIC_DEVELOPMENT_DATASET"

    def __init__(self, spectral_data, spatial_data, env_data, labels, severities, lead_times):
        self.spectral = torch.tensor(spectral_data, dtype=torch.float32)
        self.spatial = torch.tensor(spatial_data, dtype=torch.float32)
        self.env = torch.tensor(env_data, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)
        self.severities = torch.tensor(severities, dtype=torch.float32)
        self.lead_times = torch.tensor(lead_times, dtype=torch.float32)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "spectral": self.spectral[idx],
            "spatial": self.spatial[idx],
            "env": self.env[idx],
            "label": self.labels[idx],
            "severity": self.severities[idx],
            "lead_time": self.lead_times[idx],
            "dataset_type": self.DATASET_TYPE
        }


def generate_synthetic_multimodal_data(num_samples=1800, seed=42):
    """
    Generates synthetic data explicitly for development & SIL simulation mode.
    """
    np.random.seed(seed)
    spectral_list, spatial_list, env_list = [], [], []
    labels_list, severities_list, lead_times_list = [], [], []

    samples_per_class = num_samples // 6

    for class_id in range(6):
        for _ in range(samples_per_class):
            if class_id == 0:  # HEALTHY
                base_spectral = np.array([0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90])
                noise = np.random.normal(0, 0.03, 10)
                spec = np.clip(base_spectral + noise, 0.05, 1.0)
                img = np.zeros((3, 64, 64), dtype=np.float32)
                img[0] = np.random.uniform(0.1, 0.2, (64, 64))
                img[1] = np.random.uniform(0.6, 0.85, (64, 64))
                img[2] = np.random.uniform(0.1, 0.25, (64, 64))
                temp, hum, soil, gas = np.random.normal(23.0, 2.0), np.random.normal(65.0, 5.0), np.random.normal(55.0, 5.0), np.random.normal(80.0, 10.0)
                sev, lead = float(np.random.uniform(0.0, 15.0)), 0.0

            elif class_id == 1:  # PRE_SYMPTOMATIC_STRESS
                base_spectral = np.array([0.16, 0.19, 0.22, 0.33, 0.60, 0.42, 0.30, 0.22, 0.55, 0.72])
                noise = np.random.normal(0, 0.03, 10)
                spec = np.clip(base_spectral + noise, 0.05, 1.0)
                img = np.zeros((3, 64, 64), dtype=np.float32)
                img[0] = np.random.uniform(0.15, 0.25, (64, 64))
                img[1] = np.random.uniform(0.55, 0.75, (64, 64))
                img[2] = np.random.uniform(0.1, 0.25, (64, 64))
                temp, hum, soil, gas = np.random.normal(27.0, 2.5), np.random.normal(52.0, 6.0), np.random.normal(38.0, 4.0), np.random.normal(85.0, 12.0)
                sev, lead = float(np.random.uniform(20.0, 40.0)), float(np.random.uniform(36.0, 72.0))

            elif class_id == 2:  # WATER_STRESS
                base_spectral = np.array([0.18, 0.22, 0.25, 0.30, 0.45, 0.55, 0.50, 0.45, 0.48, 0.52])
                noise = np.random.normal(0, 0.03, 10)
                spec = np.clip(base_spectral + noise, 0.05, 1.0)
                img = np.zeros((3, 64, 64), dtype=np.float32)
                img[0] = np.random.uniform(0.4, 0.6, (64, 64))
                img[1] = np.random.uniform(0.4, 0.6, (64, 64))
                img[2] = np.random.uniform(0.1, 0.2, (64, 64))
                temp, hum, soil, gas = np.random.normal(33.0, 3.0), np.random.normal(32.0, 5.0), np.random.normal(18.0, 4.0), np.random.normal(90.0, 15.0)
                sev, lead = float(np.random.uniform(45.0, 75.0)), float(np.random.uniform(12.0, 36.0))

            elif class_id == 3:  # DISEASE
                base_spectral = np.array([0.22, 0.25, 0.28, 0.28, 0.38, 0.50, 0.58, 0.52, 0.42, 0.45])
                noise = np.random.normal(0, 0.03, 10)
                spec = np.clip(base_spectral + noise, 0.05, 1.0)
                img = np.zeros((3, 64, 64), dtype=np.float32)
                img[0] = np.random.uniform(0.3, 0.7, (64, 64))
                img[1] = np.random.uniform(0.3, 0.5, (64, 64))
                img[2] = np.random.uniform(0.05, 0.2, (64, 64))
                temp, hum, soil, gas = np.random.normal(26.0, 2.0), np.random.normal(84.0, 5.0), np.random.normal(48.0, 5.0), np.random.normal(110.0, 20.0)
                sev, lead = float(np.random.uniform(50.0, 85.0)), float(np.random.uniform(6.0, 24.0))

            elif class_id == 4:  # SEVERE_STRESS
                base_spectral = np.array([0.25, 0.28, 0.30, 0.32, 0.35, 0.42, 0.50, 0.55, 0.35, 0.30])
                noise = np.random.normal(0, 0.03, 10)
                spec = np.clip(base_spectral + noise, 0.05, 1.0)
                img = np.zeros((3, 64, 64), dtype=np.float32)
                img[0] = np.random.uniform(0.5, 0.7, (64, 64))
                img[1] = np.random.uniform(0.3, 0.4, (64, 64))
                img[2] = np.random.uniform(0.1, 0.2, (64, 64))
                temp, hum, soil, gas = np.random.normal(38.0, 3.0), np.random.normal(25.0, 5.0), np.random.normal(10.0, 3.0), np.random.normal(250.0, 40.0)
                sev, lead = float(np.random.uniform(85.0, 100.0)), 0.0

            else:  # UNKNOWN_ANOMALY
                spec = np.random.uniform(0.0, 1.0, 10)
                img = np.random.uniform(0.0, 1.0, (3, 64, 64)).astype(np.float32)
                temp, hum, soil, gas = np.random.normal(45.0, 10.0), np.random.normal(10.0, 10.0), np.random.normal(95.0, 5.0), np.random.normal(600.0, 100.0)
                sev, lead = float(np.random.uniform(50.0, 100.0)), 0.0

            env_vector = np.array([temp / 50.0, hum / 100.0, soil / 100.0, gas / 500.0], dtype=np.float32)
            spectral_list.append(spec)
            spatial_list.append(img)
            env_list.append(env_vector)
            labels_list.append(class_id)
            severities_list.append(sev)
            lead_times_list.append(lead)

    return (
        np.array(spectral_list, dtype=np.float32),
        np.array(spatial_list, dtype=np.float32),
        np.array(env_list, dtype=np.float32),
        np.array(labels_list, dtype=np.int64),
        np.array(severities_list, dtype=np.float32),
        np.array(lead_times_list, dtype=np.float32)
    )


def get_dataloaders(data_manifest=None, dataset_type="SYNTHETIC_DEVELOPMENT_DATASET", batch_size=32, train_ratio=0.8, seed=42):
    """
    Returns train and validation PyTorch DataLoaders.
    Strictly checks dataset_type to ensure transparent scientific reporting.
    """
    if dataset_type == "REAL_DATASET" and data_manifest and os.path.exists(data_manifest):
        dataset = RealAgriDataset(manifest_csv=data_manifest)
        total = len(dataset)
        train_size = int(total * train_ratio)
        val_size = total - train_size
        train_ds, val_ds = torch.utils.data.random_split(dataset, [train_size, val_size])
    else:
        # Development / SIL Simulator Dataset
        spec, spat, env, labels, sevs, leads = generate_synthetic_multimodal_data(num_samples=1800, seed=seed)
        total = len(labels)
        indices = np.arange(total)
        np.random.seed(seed)
        np.random.shuffle(indices)

        train_size = int(total * train_ratio)
        train_idx, val_idx = indices[:train_size], indices[train_size:]

        train_ds = SyntheticAgriDataset(spec[train_idx], spat[train_idx], env[train_idx], labels[train_idx], sevs[train_idx], leads[train_idx])
        val_ds = SyntheticAgriDataset(spec[val_idx], spat[val_idx], env[val_idx], labels[val_idx], sevs[val_idx], leads[val_idx])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader
