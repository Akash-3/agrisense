import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np

from ml.dataset import get_dataloaders
from ml.model import MMSSNet
from ml.temporal import TemporalStressNet

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")

def train_mmssnet(epochs=10, lr=1e-3, batch_size=32):
    """
    Trains MM-SSNet model on multi-modal synthetic dataset with multi-task loss function.
    """
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    print(f"=== Starting MM-SSNet Training ({epochs} epochs) ===")

    train_loader, val_loader = get_dataloaders(batch_size=batch_size)
    model = MMSSNet(num_classes=6)
    
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    cls_criterion = nn.CrossEntropyLoss()
    sev_criterion = nn.MSELoss()
    lead_criterion = nn.MSELoss()

    best_val_acc = 0.0

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct_cls = 0
        total_samples = 0

        for batch in train_loader:
            spec = batch["spectral"]
            spat = batch["spatial"]
            env = batch["env"]
            target_cls = batch["label"]
            target_sev = batch["severity"]
            target_lead = batch["lead_time"]

            optimizer.zero_grad()

            out = model(spec, spat, env)

            l_cls = cls_criterion(out["class_logits"], target_cls)
            l_sev = sev_criterion(out["severity"], target_sev)
            l_lead = lead_criterion(out["lead_time"], target_lead)

            # Combined Multi-Task Loss
            loss = l_cls + 0.01 * l_sev + 0.005 * l_lead

            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(target_cls)
            preds = torch.argmax(out["class_logits"], dim=1)
            correct_cls += (preds == target_cls).sum().item()
            total_samples += len(target_cls)

        train_loss = total_loss / total_samples
        train_acc = (correct_cls / total_samples) * 100.0

        # Validation Loop
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for batch in val_loader:
                spec = batch["spectral"]
                spat = batch["spatial"]
                env = batch["env"]
                target_cls = batch["label"]
                target_sev = batch["severity"]
                target_lead = batch["lead_time"]

                out = model(spec, spat, env)

                l_cls = cls_criterion(out["class_logits"], target_cls)
                l_sev = sev_criterion(out["severity"], target_sev)
                l_lead = lead_criterion(out["lead_time"], target_lead)
                loss = l_cls + 0.01 * l_sev + 0.005 * l_lead

                val_loss += loss.item() * len(target_cls)
                preds = torch.argmax(out["class_logits"], dim=1)
                val_correct += (preds == target_cls).sum().item()
                val_total += len(target_cls)

        val_loss /= val_total
        val_acc = (val_correct / val_total) * 100.0

        print(f"Epoch [{epoch:02d}/{epochs:02d}] - Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}% | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}%")

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            checkpoint_path = os.path.join(CHECKPOINT_DIR, "mmssnet.pth")
            torch.save({
                "model_state_dict": model.state_dict(),
                "val_acc": val_acc,
                "epoch": epoch
            }, checkpoint_path)

    print(f"MM-SSNet Training Complete! Best Val Accuracy: {best_val_acc:.2f}%. Saved to {os.path.join(CHECKPOINT_DIR, 'mmssnet.pth')}\n")
    return model

def train_temporal_net(epochs=10, lr=1e-3, batch_size=32):
    """
    Trains TemporalStressNet model on synthetic sequential telemetry sequences.
    """
    print(f"=== Starting TemporalStressNet Training ({epochs} epochs) ===")
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    # Generate synthetic sequence dataset (10 timesteps per sample)
    np.random.seed(42)
    num_samples = 1000
    seq_len = 10
    in_features = 15

    X_seq = np.random.uniform(0.1, 1.0, (num_samples, seq_len, in_features)).astype(np.float32)
    y_trend = np.random.randint(0, 4, num_samples)
    y_fut_sev = np.random.uniform(10.0, 90.0, num_samples).astype(np.float32)

    X_tensor = torch.tensor(X_seq)
    y_trend_tensor = torch.tensor(y_trend, dtype=torch.long)
    y_fut_sev_tensor = torch.tensor(y_fut_sev, dtype=torch.float32)

    dataset = torch.utils.data.TensorDataset(X_tensor, y_trend_tensor, y_fut_sev_tensor)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = TemporalStressNet(in_features=15, hidden_dim=64, num_classes=4)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    cls_criterion = nn.CrossEntropyLoss()
    sev_criterion = nn.MSELoss()

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for x_b, y_tr_b, y_sev_b in loader:
            optimizer.zero_grad()
            out = model(x_b)

            loss_tr = cls_criterion(out["trend_logits"], y_tr_b)
            loss_sev = sev_criterion(out["future_severity"], y_sev_b)
            loss = loss_tr + 0.01 * loss_sev

            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(y_tr_b)
            preds = torch.argmax(out["trend_logits"], dim=1)
            correct += (preds == y_tr_b).sum().item()
            total += len(y_tr_b)

        acc = (correct / total) * 100.0
        print(f"Temporal Epoch [{epoch:02d}/{epochs:02d}] - Loss: {total_loss/total:.4f} | Acc: {acc:.2f}%")

    checkpoint_path = os.path.join(CHECKPOINT_DIR, "temporal_net.pth")
    torch.save({"model_state_dict": model.state_dict()}, checkpoint_path)
    print(f"TemporalStressNet Saved to {checkpoint_path}\n")
    return model

if __name__ == "__main__":
    train_mmssnet(epochs=10)
    train_temporal_net(epochs=10)
