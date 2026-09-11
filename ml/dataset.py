import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

CONDITION_LABELS = {
    0: "HEALTHY",
    1: "PRE_SYMPTOMATIC_STRESS",
    2: "WATER_STRESS",
    3: "DISEASE",
    4: "SEVERE_STRESS",
    5: "UNKNOWN_ANOMALY"
}

LABEL_TO_ID = {v: k for k, v in CONDITION_LABELS.items()}

class AgriSenseDataset(Dataset):
    """
    Multimodal Agricultural Dataset for MM-SSNet.
    Includes:
    - Spectral: 10-channel AS7341 optical spectrum (415nm - 850nm)
    - Spatial: (3, 64, 64) RGB crop canopy synthetic patch
    - Environmental: 4-channel telemetry [temp_c, humidity_pct, soil_moisture_pct, gas_ppm]
    """
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
            "lead_time": self.lead_times[idx]
        }

def generate_synthetic_multimodal_data(num_samples=1500, seed=42):
    """
    Generates realistic, physically grounded multi-modal data for crop stress diagnosis.
    1. Spectral 10-band profile (AS7341 wavelengths: 415, 445, 480, 515, 555, 590, 630, 680, 730, 850 nm)
    2. Spatial 64x64 RGB canopy tensor
    3. Environmental telemetry [Temp, Humidity, Soil Moisture, Gas]
    4. Targets: Class, Severity (0-100), Lead-Time (hours)
    """
    np.random.seed(seed)
    
    spectral_list = []
    spatial_list = []
    env_list = []
    labels_list = []
    severities_list = []
    lead_times_list = []

    samples_per_class = num_samples // 6

    for class_id in range(6):
        for _ in range(samples_per_class):
            if class_id == 0:  # HEALTHY
                # High NIR (850nm), moderate green (555nm), low red (680nm)
                base_spectral = np.array([0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90])
                noise = np.random.normal(0, 0.03, 10)
                spec = np.clip(base_spectral + noise, 0.05, 1.0)
                
                # RGB Image: Dominant Vibrant Green
                img = np.zeros((3, 64, 64), dtype=np.float32)
                img[0] = np.random.uniform(0.1, 0.2, (64, 64))  # R
                img[1] = np.random.uniform(0.6, 0.85, (64, 64)) # G
                img[2] = np.random.uniform(0.1, 0.25, (64, 64)) # B
                
                # Env: Optimal
                temp = np.random.normal(23.0, 2.0)
                hum = np.random.normal(65.0, 5.0)
                soil = np.random.normal(55.0, 5.0)
                gas = np.random.normal(80.0, 10.0)
                
                sev = float(np.random.uniform(0.0, 15.0))
                lead = 0.0

            elif class_id == 1:  # PRE_SYMPTOMATIC_STRESS
                # Early shift in Red-Edge (730nm) and NIR drop, while RGB looks almost normal green
                base_spectral = np.array([0.16, 0.19, 0.22, 0.33, 0.60, 0.42, 0.30, 0.22, 0.55, 0.72])
                noise = np.random.normal(0, 0.03, 10)
                spec = np.clip(base_spectral + noise, 0.05, 1.0)
                
                # RGB Image: Visual canopy looks normal green with subtle dullness
                img = np.zeros((3, 64, 64), dtype=np.float32)
                img[0] = np.random.uniform(0.15, 0.25, (64, 64)) # R
                img[1] = np.random.uniform(0.55, 0.75, (64, 64)) # G
                img[2] = np.random.uniform(0.1, 0.25, (64, 64))  # B
                
                # Env: Slight elevated temperature or subtle soil drying
                temp = np.random.normal(27.0, 2.5)
                hum = np.random.normal(52.0, 6.0)
                soil = np.random.normal(38.0, 4.0)
                gas = np.random.normal(85.0, 12.0)
                
                sev = float(np.random.uniform(20.0, 40.0))
                lead = float(np.random.uniform(36.0, 72.0)) # 36-72 hours early detection

            elif class_id == 2:  # WATER_STRESS
                # Sharp NIR drop, elevated reflectance in yellow/red channels
                base_spectral = np.array([0.18, 0.22, 0.25, 0.30, 0.45, 0.55, 0.50, 0.45, 0.48, 0.52])
                noise = np.random.normal(0, 0.03, 10)
                spec = np.clip(base_spectral + noise, 0.05, 1.0)
                
                # RGB Image: Yellowish-green foliage with dry soil patches
                img = np.zeros((3, 64, 64), dtype=np.float32)
                img[0] = np.random.uniform(0.4, 0.6, (64, 64)) # Elevated R
                img[1] = np.random.uniform(0.4, 0.6, (64, 64)) # Yellowish G
                img[2] = np.random.uniform(0.1, 0.2, (64, 64)) # B
                
                # Env: Low soil moisture, high temp, low humidity
                temp = np.random.normal(33.0, 3.0)
                hum = np.random.normal(32.0, 5.0)
                soil = np.random.normal(18.0, 4.0)
                gas = np.random.normal(90.0, 15.0)
                
                sev = float(np.random.uniform(45.0, 75.0))
                lead = float(np.random.uniform(12.0, 36.0))

            elif class_id == 3:  # DISEASE
                # Depressed green reflectance, elevated red/yellow, patchy NIR
                base_spectral = np.array([0.22, 0.25, 0.28, 0.28, 0.38, 0.50, 0.58, 0.52, 0.42, 0.45])
                noise = np.random.normal(0, 0.03, 10)
                spec = np.clip(base_spectral + noise, 0.05, 1.0)
                
                # RGB Image: Brown necrotic lesions / chlorotic spots on leaf background
                img = np.zeros((3, 64, 64), dtype=np.float32)
                img[0] = np.random.uniform(0.3, 0.7, (64, 64)) # Brownish Red
                img[1] = np.random.uniform(0.3, 0.5, (64, 64))
                img[2] = np.random.uniform(0.05, 0.2, (64, 64))
                # Add synthetic necrotic spots (dark circular regions)
                for _ in range(3):
                    cx, cy = np.random.randint(10, 54, 2)
                    r = np.random.randint(4, 10)
                    y, x = np.ogrid[:64, :64]
                    mask = (x - cx)**2 + (y - cy)**2 <= r**2
                    img[0, mask] = 0.2  # Dark necrotic center
                    img[1, mask] = 0.15
                    img[2, mask] = 0.05
                
                # Env: High humidity (fungal risk), moderate temp, normal soil
                temp = np.random.normal(26.0, 2.0)
                hum = np.random.normal(84.0, 5.0)
                soil = np.random.normal(48.0, 5.0)
                gas = np.random.normal(110.0, 20.0)
                
                sev = float(np.random.uniform(50.0, 85.0))
                lead = float(np.random.uniform(6.0, 24.0))

            elif class_id == 4:  # SEVERE_STRESS
                # Collapse of NIR reflectance, flat degraded spectrum across all bands
                base_spectral = np.array([0.25, 0.28, 0.30, 0.32, 0.35, 0.42, 0.50, 0.55, 0.35, 0.30])
                noise = np.random.normal(0, 0.03, 10)
                spec = np.clip(base_spectral + noise, 0.05, 1.0)
                
                # RGB Image: Withered, brown/gray canopy
                img = np.zeros((3, 64, 64), dtype=np.float32)
                img[0] = np.random.uniform(0.5, 0.7, (64, 64))
                img[1] = np.random.uniform(0.3, 0.4, (64, 64))
                img[2] = np.random.uniform(0.1, 0.2, (64, 64))
                
                # Env: Extreme environmental stress (high gas or critical moisture drop)
                temp = np.random.normal(38.0, 3.0)
                hum = np.random.normal(25.0, 5.0)
                soil = np.random.normal(10.0, 3.0)
                gas = np.random.normal(250.0, 40.0)
                
                sev = float(np.random.uniform(85.0, 100.0))
                lead = 0.0

            else:  # UNKNOWN_ANOMALY
                # Out-of-Distribution profile (e.g. sensor malfunction or unknown chemical contamination)
                spec = np.random.uniform(0.0, 1.0, 10)
                img = np.random.uniform(0.0, 1.0, (3, 64, 64)).astype(np.float32)
                temp = np.random.normal(45.0, 10.0)
                hum = np.random.normal(10.0, 10.0)
                soil = np.random.normal(95.0, 5.0)
                gas = np.random.normal(600.0, 100.0)
                
                sev = float(np.random.uniform(50.0, 100.0))
                lead = 0.0

            # Normalize env values: [temp/50, hum/100, soil/100, gas/500]
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

def get_dataloaders(batch_size=32, train_ratio=0.8, seed=42):
    """
    Returns train and validation PyTorch DataLoaders.
    """
    spec, spat, env, labels, sevs, leads = generate_synthetic_multimodal_data(num_samples=1800, seed=seed)
    
    total = len(labels)
    indices = np.arange(total)
    np.random.seed(seed)
    np.random.shuffle(indices)

    train_size = int(total * train_ratio)
    train_idx, val_idx = indices[:train_size], indices[train_size:]

    train_ds = AgriSenseDataset(
        spec[train_idx], spat[train_idx], env[train_idx],
        labels[train_idx], sevs[train_idx], leads[train_idx]
    )
    val_ds = AgriSenseDataset(
        spec[val_idx], spat[val_idx], env[val_idx],
        labels[val_idx], sevs[val_idx], leads[val_idx]
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader
