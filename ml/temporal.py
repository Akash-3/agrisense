import torch
import torch.nn as nn
import torch.nn.functional as F

TREND_LABELS = {
    0: "STABLE",
    1: "IMPROVING",
    2: "DETERIORATING",
    3: "RAPID_DETERIORATION"
}

class TemporalStressNet(nn.Module):
    """
    GRU-based Temporal Sequence Model for crop stress trajectory prediction over multi-timestep historical sequences.
    Input sequence shape: (B, Seq_Len, Feature_Dim) e.g. (B, 10, 15) containing [spectral (10), env (4), prev_sev (1)]
    Outputs:
    - Trend Classification Logits (4 classes)
    - Future Severity Projection (0-100)
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
        # x_seq: (B, Seq_Len, In_Features)
        out, h_n = self.gru(x_seq)
        last_hidden = out[:, -1, :] # Last timestep output: (B, hidden_dim)

        trend_logits = self.trend_head(last_hidden)
        future_severity = self.future_severity_head(last_hidden) * 100.0

        return {
            "trend_logits": trend_logits,
            "future_severity": future_severity.squeeze(-1)
        }
