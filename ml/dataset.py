import os
import csv
import yaml
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

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "synthetic_config.yaml")

def load_synthetic_config(config_path=None):
    """
    Loads synthetic dataset configuration from YAML file.
    """
    path = config_path or DEFAULT_CONFIG_PATH
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"[load_synthetic_config] Warning: Error loading {path} ({e}). Using default settings.")
    
    return {
        "dataset_type": "synthetic_development",
        "real_world_validation": False,
        "generator": {
            "num_samples": 1800,
            "random_seed": 42,
            "spectral_noise_std": 0.03,
            "environment_noise_std": 0.05,
            "image_noise_std": 0.05,
            "class_overlap_probability": 0.15,
            "missing_modality_probability": 0.10
        }
    }


class BaseAgriSenseDataset(Dataset):
    """
    Abstract base class for all AgriSense datasets.
    Enforces dataset_type and real_world_validation attributes to ensure scientific honesty.
    """
    def __init__(self, dataset_type="synthetic_development", real_world_validation=False):
        self.dataset_type = dataset_type
        self.real_world_validation = real_world_validation

    def __len__(self):
        raise NotImplementedError

    def __getitem__(self, idx):
        raise NotImplementedError


class RealAgriSenseDataset(BaseAgriSenseDataset):
    """
    Real-world paired crop observation dataset.
    Loads actual RGB images, AS7341 spectral channels, and environmental telemetry from disk / CSV manifest.
    """
    def __init__(self, manifest_csv, img_dir=None, transform=None):
        super().__init__(dataset_type="real_dataset", real_world_validation=True)
        self.manifest_path = manifest_csv
        self.img_dir = img_dir or os.path.dirname(manifest_csv)
        self.transform = transform
        self.samples = []
        self._load_manifest()

    def _load_manifest(self):
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"[RealAgriSenseDataset] Manifest CSV not found at: {self.manifest_path}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                spec = [float(row.get(f"f{i+1}", row.get(f"spectral_{i}", 0.1))) for i in range(10)]
                env = [
                    float(row.get("temp_c", 25.0)) / 50.0,
                    float(row.get("hum_pct", 60.0)) / 100.0,
                    float(row.get("soil_moisture_pct", 50.0)) / 100.0,
                    float(row.get("gas_ppm", 80.0)) / 500.0
                ]
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

        print(f"[RealAgriSenseDataset] Loaded {len(self.samples)} REAL crop observation samples from {self.manifest_path}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        has_spatial = False

        if s["img_path"] and os.path.exists(s["img_path"]):
            try:
                img = Image.open(s["img_path"]).convert("RGB").resize((64, 64))
                spat_arr = np.array(img, dtype=np.float32).transpose(2, 0, 1) / 255.0
                has_spatial = True
            except Exception:
                spat_arr = np.zeros((3, 64, 64), dtype=np.float32)
        else:
            spat_arr = np.zeros((3, 64, 64), dtype=np.float32)

        return {
            "spectral": torch.tensor(s["spectral"], dtype=torch.float32),
            "spatial": torch.tensor(spat_arr, dtype=torch.float32),
            "spatial_available": torch.tensor(has_spatial, dtype=torch.bool),
            "env": torch.tensor(s["env"], dtype=torch.float32),
            "label": torch.tensor(s["label"], dtype=torch.long),
            "severity": torch.tensor(s["severity"], dtype=torch.float32),
            "lead_time": torch.tensor(s["lead_time"], dtype=torch.float32),
            "dataset_type": self.dataset_type,
            "real_world_validation": self.real_world_validation
        }


class SyntheticAgriSenseDataset(BaseAgriSenseDataset):
    """
    Synthetic development dataset class.
    Explicitly labeled as synthetic_development with real_world_validation = False.
    """
    def __init__(self, spectral_data, spatial_data, env_data, labels, severities, lead_times, spatial_mask=None):
        super().__init__(dataset_type="synthetic_development", real_world_validation=False)
        self.spectral = torch.tensor(spectral_data, dtype=torch.float32)
        self.spatial = torch.tensor(spatial_data, dtype=torch.float32)
        self.env = torch.tensor(env_data, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)
        self.severities = torch.tensor(severities, dtype=torch.float32)
        self.lead_times = torch.tensor(lead_times, dtype=torch.float32)
        
        if spatial_mask is not None:
            self.spatial_available = torch.tensor(spatial_mask, dtype=torch.bool)
        else:
            # Check if spatial is non-zero
            self.spatial_available = (self.spatial.abs().sum(dim=(1, 2, 3)) > 1e-4)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "spectral": self.spectral[idx],
            "spatial": self.spatial[idx],
            "spatial_available": self.spatial_available[idx],
            "env": self.env[idx],
            "label": self.labels[idx],
            "severity": self.severities[idx],
            "lead_time": self.lead_times[idx],
            "dataset_type": self.dataset_type,
            "real_world_validation": self.real_world_validation
        }

# Backwards compatibility aliases
RealAgriDataset = RealAgriSenseDataset
SyntheticAgriDataset = SyntheticAgriSenseDataset


def generate_synthetic_multimodal_data(num_samples=1800, seed=42, config_path=None):
    """
    Generates synthetic multimodal crop stress data driven by synthetic_config.yaml.
    Includes controlled class feature overlap so multimodal fusion is required for disambiguation.
    """
    cfg = load_synthetic_config(config_path)
    gen_cfg = cfg.get("generator", {})
    
    spec_noise_std = gen_cfg.get("spectral_noise_std", 0.03)
    overlap_prob = gen_cfg.get("class_overlap_probability", 0.15)
    missing_spatial_prob = gen_cfg.get("missing_modality_probability", 0.10)

    np.random.seed(seed)
    spectral_list, spatial_list, env_list = [], [], []
    labels_list, severities_list, lead_times_list = [], [], []
    spatial_mask_list = []

    samples_per_class = num_samples // 6

    # Class feature prototypes
    class_prototypes = {
        0: { # HEALTHY
            "spectral": np.array([0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90]),
            "env": (23.0, 65.0, 55.0, 80.0), # temp, hum, soil, gas
            "rgb": (0.15, 0.75, 0.15),
            "sev_range": (0.0, 15.0),
            "lead": 0.0
        },
        1: { # PRE_SYMPTOMATIC_STRESS
            "spectral": np.array([0.16, 0.19, 0.22, 0.33, 0.60, 0.42, 0.30, 0.22, 0.55, 0.72]),
            "env": (27.0, 52.0, 38.0, 85.0),
            "rgb": (0.20, 0.65, 0.15),
            "sev_range": (20.0, 40.0),
            "lead_range": (36.0, 72.0)
        },
        2: { # WATER_STRESS
            "spectral": np.array([0.18, 0.22, 0.25, 0.30, 0.45, 0.55, 0.50, 0.45, 0.48, 0.52]),
            "env": (33.0, 32.0, 18.0, 90.0),
            "rgb": (0.50, 0.50, 0.15),
            "sev_range": (45.0, 75.0),
            "lead_range": (12.0, 36.0)
        },
        3: { # DISEASE
            "spectral": np.array([0.22, 0.25, 0.28, 0.28, 0.38, 0.50, 0.58, 0.52, 0.42, 0.45]),
            "env": (26.0, 84.0, 48.0, 110.0),
            "rgb": (0.50, 0.40, 0.10),
            "sev_range": (50.0, 85.0),
            "lead_range": (6.0, 24.0)
        },
        4: { # SEVERE_STRESS
            "spectral": np.array([0.25, 0.28, 0.30, 0.32, 0.35, 0.42, 0.50, 0.55, 0.35, 0.30]),
            "env": (38.0, 25.0, 10.0, 250.0),
            "rgb": (0.60, 0.35, 0.15),
            "sev_range": (85.0, 100.0),
            "lead": 0.0
        },
        5: { # UNKNOWN_ANOMALY
            "spectral": None, # Random
            "env": (45.0, 10.0, 95.0, 600.0),
            "rgb": None,
            "sev_range": (50.0, 100.0),
            "lead": 0.0
        }
    }

    for class_id in range(6):
        proto = class_prototypes[class_id]
        
        for _ in range(samples_per_class):
            # Check for controlled class feature overlap
            is_overlap = (np.random.rand() < overlap_prob) and (class_id in [1, 2, 3])
            
            if class_id == 5:
                # Anomaly
                spec = np.random.uniform(0.0, 1.0, 10)
                img = np.random.uniform(0.0, 1.0, (3, 64, 64)).astype(np.float32)
                temp, hum, soil, gas = np.random.normal(45.0, 10.0), np.random.normal(10.0, 10.0), np.random.normal(95.0, 5.0), np.random.normal(600.0, 100.0)
                sev = float(np.random.uniform(50.0, 100.0))
                lead = 0.0
            else:
                base_spec = proto["spectral"].copy()
                t_mean, h_mean, s_mean, g_mean = proto["env"]
                r_c, g_c, b_c = proto["rgb"]

                if is_overlap:
                    # Blend with neighboring class prototype to create controlled ambiguity in 1 modality
                    neighbor_id = (class_id + 1) if class_id < 3 else (class_id - 1)
                    neighbor_proto = class_prototypes[neighbor_id]
                    # Blend spectral towards neighbor (50% blend)
                    base_spec = 0.5 * base_spec + 0.5 * neighbor_proto["spectral"]

                noise = np.random.normal(0, spec_noise_std, 10)
                spec = np.clip(base_spec + noise, 0.05, 1.0)

                temp = np.random.normal(t_mean, 2.5)
                hum = np.random.normal(h_mean, 5.0)
                soil = np.random.normal(s_mean, 5.0)
                gas = np.random.normal(g_mean, 15.0)

                # Spatial RGB tensor
                img = np.zeros((3, 64, 64), dtype=np.float32)
                img[0] = np.random.uniform(r_c - 0.05, r_c + 0.05, (64, 64))
                img[1] = np.random.uniform(g_c - 0.05, g_c + 0.05, (64, 64))
                img[2] = np.random.uniform(b_c - 0.05, b_c + 0.05, (64, 64))
                img = np.clip(img, 0.0, 1.0)

                sev = float(np.random.uniform(*proto["sev_range"]))
                if "lead_range" in proto:
                    lead = float(np.random.uniform(*proto["lead_range"]))
                else:
                    lead = float(proto["lead"])

            # Missing spatial modality simulation
            has_spatial = True
            if np.random.rand() < missing_spatial_prob:
                img = np.zeros((3, 64, 64), dtype=np.float32)
                has_spatial = False

            env_vector = np.array([temp / 50.0, hum / 100.0, soil / 100.0, gas / 500.0], dtype=np.float32)

            spectral_list.append(spec)
            spatial_list.append(img)
            spatial_mask_list.append(has_spatial)
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
        np.array(lead_times_list, dtype=np.float32),
        np.array(spatial_mask_list, dtype=bool)
    )


def get_dataloaders(data_manifest=None, dataset_type="synthetic_development", batch_size=32, train_ratio=0.8, seed=42):
    """
    Returns train and validation PyTorch DataLoaders.
    Strictly enforces dataset_type reporting.
    """
    if (dataset_type == "real_dataset" or dataset_type == "REAL_DATASET") and data_manifest and os.path.exists(data_manifest):
        dataset = RealAgriSenseDataset(manifest_csv=data_manifest)
        total = len(dataset)
        train_size = int(total * train_ratio)
        val_size = total - train_size
        train_ds, val_ds = torch.utils.data.random_split(dataset, [train_size, val_size])
    else:
        # Development / SIL Simulator Dataset
        spec, spat, env, labels, sevs, leads, masks = generate_synthetic_multimodal_data(num_samples=1800, seed=seed)
        total = len(labels)
        indices = np.arange(total)
        np.random.seed(seed)
        np.random.shuffle(indices)

        train_size = int(total * train_ratio)
        train_idx, val_idx = indices[:train_size], indices[train_size:]

        train_ds = SyntheticAgriSenseDataset(spec[train_idx], spat[train_idx], env[train_idx], labels[train_idx], sevs[train_idx], leads[train_idx], masks[train_idx])
        val_ds = SyntheticAgriSenseDataset(spec[val_idx], spat[val_idx], env[val_idx], labels[val_idx], sevs[val_idx], leads[val_idx], masks[val_idx])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader
