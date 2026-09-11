import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as tv_models

class SpectralEncoder1D(nn.Module):
    """
    Stream 1: 1D Convolutional Encoder for 10-Channel AS7341 Spectral Band Input (415nm - 850nm)
    """
    def __init__(self, in_channels=1, embed_dim=128):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(32)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(64)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Linear(64, embed_dim)

    def forward(self, x):
        # x: (B, 10) -> reshape to (B, 1, 10)
        if x.dim() == 2:
            x = x.unsqueeze(1)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.pool(x).squeeze(-1) # (B, 64)
        out = self.fc(x)             # (B, embed_dim)
        return out


class SpatialEncoder2D(nn.Module):
    """
    Stream 2: PyTorch MobileNetV3-Small Backbone for RGB Crop Canopy Imagery
    Instantiates genuine MobileNetV3 architecture with AdaptiveAvgPool & FC projection head.
    """
    def __init__(self, in_channels=3, embed_dim=128):
        super().__init__()
        try:
            weights = tv_models.MobileNet_V3_Small_Weights.DEFAULT
            self.backbone = tv_models.mobilenet_v3_small(weights=weights)
        except Exception:
            self.backbone = tv_models.mobilenet_v3_small(weights=None)

        in_features = self.backbone.classifier[0].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.Hardswish(),
            nn.Dropout(p=0.2, inplace=True),
            nn.Linear(256, embed_dim)
        )

    def forward(self, x):
        # x: (B, 3, H, W)
        return self.backbone(x)


class EnvironmentalEncoder(nn.Module):
    """
    Stream 3: MLP Encoder for 4-Channel Environmental Metrics [Temp, Humidity, Soil Moisture, Gas]
    """
    def __init__(self, in_features=4, embed_dim=64):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(in_features, 32),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            nn.Linear(32, embed_dim),
            nn.ReLU()
        )

    def forward(self, x):
        return self.mlp(x)


class CrossAttentionFusion(nn.Module):
    """
    Spectral-Spatial Cross-Attention + Environmental Concatenation Layer
    Handles missing spatial/spectral streams seamlessly.
    """
    def __init__(self, embed_dim=128, env_dim=64, num_heads=4):
        super().__init__()
        self.cross_attn = nn.MultiheadAttention(embed_dim=embed_dim, num_heads=num_heads, batch_first=True)
        self.layer_norm = nn.LayerNorm(embed_dim)
        self.fusion_fc = nn.Sequential(
            nn.Linear(embed_dim + env_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2)
        )

    def forward(self, spec_emb, spat_emb, env_emb, spat_available=True):
        # spec_emb: (B, 128), spat_emb: (B, 128), env_emb: (B, 64)
        if spat_available and spat_emb is not None:
            q = spat_emb.unsqueeze(1)
            k = spec_emb.unsqueeze(1)
            v = spec_emb.unsqueeze(1)

            attn_out, attn_weights = self.cross_attn(q, k, v)
            attn_out = attn_out.squeeze(1)
            spatial_spectral_fused = self.layer_norm(spat_emb + attn_out)
        else:
            # Missing spatial stream fallback: use spectral embedding directly
            spatial_spectral_fused = spec_emb
            attn_weights = torch.zeros((spec_emb.size(0), 1, 1), device=spec_emb.device)

        concat_features = torch.cat([spatial_spectral_fused, env_emb], dim=-1) # (B, 192)
        fused_embedding = self.fusion_fc(concat_features)                      # (B, 128)

        return fused_embedding, attn_weights


class MMSSNet(nn.Module):
    """
    Multi-Modal Spectral-Spatial Network (MM-SSNet)
    Backbone: MobileNetV3-Small (Spatial) + 1D Conv (Spectral) + MLP (Environmental)
    Supports missing spatial modality inference without manufacturing fake images.
    """
    def __init__(self, num_classes=6, embed_dim=128, env_dim=64):
        super().__init__()
        self.embed_dim = embed_dim
        self.spectral_stream = SpectralEncoder1D(in_channels=1, embed_dim=embed_dim)
        self.spatial_stream = SpatialEncoder2D(in_channels=3, embed_dim=embed_dim)
        self.env_stream = EnvironmentalEncoder(in_features=4, embed_dim=env_dim)
        self.fusion = CrossAttentionFusion(embed_dim=embed_dim, env_dim=env_dim)

        self.class_head = nn.Linear(embed_dim, num_classes)
        self.severity_head = nn.Sequential(
            nn.Linear(embed_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        self.lead_time_head = nn.Sequential(
            nn.Linear(embed_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.ReLU()
        )

    def forward(self, spectral, spatial=None, env=None):
        spec_emb = self.spectral_stream(spectral)
        
        if env is None:
            # Default zero env
            env = torch.zeros((spectral.size(0), 4), device=spectral.device)
        env_emb = self.env_stream(env)

        spat_available = False
        spat_emb = None

        if spatial is not None:
            # Check if spatial tensor is valid non-zero image
            if isinstance(spatial, torch.Tensor) and spatial.abs().sum() > 1e-4:
                spat_emb = self.spatial_stream(spatial)
                spat_available = True

        fused_emb, attn_weights = self.fusion(spec_emb, spat_emb, env_emb, spat_available=spat_available)

        class_logits = self.class_head(fused_emb)
        severity = self.severity_head(fused_emb) * 100.0
        lead_time = self.lead_time_head(fused_emb)

        return {
            "class_logits": class_logits,
            "severity": severity.squeeze(-1),
            "lead_time": lead_time.squeeze(-1),
            "attn_weights": attn_weights,
            "latent_features": fused_emb,
            "spatial_modality_available": spat_available
        }
