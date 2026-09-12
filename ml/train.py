import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np

from ml.dataset import get_dataloaders
from ml.model import MMSSNet
from ml.temporal import (
    TemporalStressNet,
    SyntheticTemporalDataset,
    RealTemporalDataset,
    generate_synthetic_temporal_data,
)

CHECKPOINT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "checkpoints")
)


def calibrate_ood_detector(model, train_loader, device="cpu"):
    """
    Fits Mahalanobis Out-Of-Distribution (OOD) detector on reference
    healthy baseline latent embeddings.

    Saves mean_vector, cov_inv, and threshold to
    ml/checkpoints/ood_calibration.json.

    NO HARDCODED ZERO-MEAN OR IDENTITY COVARIANCE.
    """
    print(
        "[OOD Calibration] Extracting latent embeddings "
        "from baseline training samples..."
    )

    model.eval()
    healthy_latent_features = []

    with torch.no_grad():
        for batch in train_loader:
            spec = batch["spectral"].to(device)
            spat = batch["spatial"].to(device)
            env = batch["env"].to(device)
            labels = batch["label"].to(device)

            out = model(spec, spat, env)
            latents = out["latent_features"]

            # Select healthy baseline samples (label 0)
            healthy_mask = labels == 0

            if healthy_mask.sum() > 0:
                healthy_latent_features.extend(
                    latents[healthy_mask].cpu().numpy()
                )

    if not healthy_latent_features:
        # Fallback to all samples if no healthy class labels exist
        print(
            "[OOD Calibration] Warning: No class 0 healthy samples found. "
            "Using full dataset for calibration."
        )

        for batch in train_loader:
            spec = batch["spectral"].to(device)
            spat = batch["spatial"].to(device)
            env = batch["env"].to(device)

            out = model(spec, spat, env)

            healthy_latent_features.extend(
                out["latent_features"].cpu().numpy()
            )

    healthy_arr = np.array(
        healthy_latent_features,
        dtype=np.float64,
    )

    mean_vec = np.mean(
        healthy_arr,
        axis=0,
    )

    # Compute empirical covariance matrix with shrinkage
    # for numerical stability.
    cov_matrix = (
        np.cov(
            healthy_arr,
            rowvar=False,
        )
        + 1e-4 * np.eye(healthy_arr.shape[1])
    )

    cov_inv = np.linalg.inv(cov_matrix)

    # Compute Mahalanobis distances for calibration samples
    diffs = healthy_arr - mean_vec

    dists = [
        np.sqrt(
            np.dot(
                np.dot(d, cov_inv),
                d.T,
            )
        )
        for d in diffs
    ]

    threshold = float(
        np.percentile(
            dists,
            95,
        )
    )

    calib_path = os.path.join(
        CHECKPOINT_DIR,
        "ood_calibration.json",
    )

    calib_data = {
        "mean_vector": mean_vec.tolist(),
        "cov_inv": cov_inv.tolist(),
        "threshold": threshold,
        "latent_dim": int(
            healthy_arr.shape[1]
        ),
        "num_calibration_samples": int(
            len(healthy_arr)
        ),
        "is_calibrated": True,
        "calibration_method": (
            "Empirical Mahalanobis Distance "
            "(95th Percentile Shrinkage)"
        ),
    }

    with open(calib_path, "w") as f:
        json.dump(
            calib_data,
            f,
            indent=2,
        )

    print(
        "[OOD Calibration] Successfully calibrated "
        f"OOD Detector! Threshold={threshold:.4f}. "
        f"Saved to {calib_path}"
    )

    return calib_data


def train_mmssnet(
    epochs=10,
    lr=1e-3,
    batch_size=32,
    dataset_type="SYNTHETIC_DEVELOPMENT_DATASET",
    manifest_path=None,
    seed=42,
):
    """
    Trains MM-SSNet (MobileNetV3 backbone) model on
    multi-modal dataset.

    The seed controls NumPy, PyTorch and CUDA RNG state and
    is passed into the dataloader construction so that the
    training experiment is reproducible under deterministic
    runtime conditions.
    """

    os.makedirs(
        CHECKPOINT_DIR,
        exist_ok=True,
    )

    # ------------------------------------------------------------------
    # Reproducibility / experiment seed
    # ------------------------------------------------------------------
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print(
        f"=== Starting MM-SSNet Training "
        f"({epochs} epochs, Device: {device}, "
        f"Dataset: {dataset_type}, Seed: {seed}) ==="
    )

    # Pass the experiment seed into dataset/dataloader construction.
    train_loader, val_loader = get_dataloaders(
        data_manifest=manifest_path,
        dataset_type=dataset_type,
        batch_size=batch_size,
        seed=seed,
    )

    model = MMSSNet(
        num_classes=6
    ).to(device)

    optimizer = optim.Adam(
        model.parameters(),
        lr=lr,
        weight_decay=1e-4,
    )

    cls_criterion = nn.CrossEntropyLoss()
    sev_criterion = nn.MSELoss()
    lead_criterion = nn.MSELoss()

    best_val_acc = 0.0

    for epoch in range(
        1,
        epochs + 1,
    ):
        # --------------------------------------------------------------
        # Training
        # --------------------------------------------------------------
        model.train()

        total_loss = 0.0
        correct_cls = 0
        total_samples = 0

        for batch in train_loader:
            spec = batch["spectral"].to(device)
            spat = batch["spatial"].to(device)
            env = batch["env"].to(device)

            target_cls = batch["label"].to(device)
            target_sev = batch["severity"].to(device)
            target_lead = batch["lead_time"].to(device)

            optimizer.zero_grad()

            out = model(
                spec,
                spat,
                env,
            )

            l_cls = cls_criterion(
                out["class_logits"],
                target_cls,
            )

            l_sev = sev_criterion(
                out["severity"],
                target_sev,
            )

            l_lead = lead_criterion(
                out["lead_time"],
                target_lead,
            )

            loss = (
                l_cls
                + 0.01 * l_sev
                + 0.005 * l_lead
            )

            loss.backward()
            optimizer.step()

            total_loss += (
                loss.item()
                * len(target_cls)
            )

            preds = torch.argmax(
                out["class_logits"],
                dim=1,
            )

            correct_cls += (
                preds == target_cls
            ).sum().item()

            total_samples += len(
                target_cls
            )

        train_loss = (
            total_loss / total_samples
        )

        train_acc = (
            correct_cls
            / total_samples
        ) * 100.0

        # --------------------------------------------------------------
        # Validation
        # --------------------------------------------------------------
        model.eval()

        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for batch in val_loader:
                spec = batch["spectral"].to(device)
                spat = batch["spatial"].to(device)
                env = batch["env"].to(device)

                target_cls = batch["label"].to(device)
                target_sev = batch["severity"].to(device)
                target_lead = batch["lead_time"].to(device)

                out = model(
                    spec,
                    spat,
                    env,
                )

                l_cls = cls_criterion(
                    out["class_logits"],
                    target_cls,
                )

                l_sev = sev_criterion(
                    out["severity"],
                    target_sev,
                )

                l_lead = lead_criterion(
                    out["lead_time"],
                    target_lead,
                )

                loss = (
                    l_cls
                    + 0.01 * l_sev
                    + 0.005 * l_lead
                )

                val_loss += (
                    loss.item()
                    * len(target_cls)
                )

                preds = torch.argmax(
                    out["class_logits"],
                    dim=1,
                )

                val_correct += (
                    preds == target_cls
                ).sum().item()

                val_total += len(
                    target_cls
                )

        val_loss /= val_total

        val_acc = (
            val_correct
            / val_total
        ) * 100.0

        print(
            f"Epoch [{epoch:02d}/{epochs:02d}] - "
            f"Train Loss: {train_loss:.4f} | "
            f"Train Acc: {train_acc:.2f}% | "
            f"Val Loss: {val_loss:.4f} | "
            f"Val Acc: {val_acc:.2f}%"
        )

        # --------------------------------------------------------------
        # Save best validation checkpoint
        # --------------------------------------------------------------
        if val_acc >= best_val_acc:
            best_val_acc = val_acc

            checkpoint_path = os.path.join(
                CHECKPOINT_DIR,
                "mmssnet.pth",
            )

            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "val_acc": val_acc,
                    "epoch": epoch,
                    "dataset_type": dataset_type,
                    "backbone": "MobileNetV3-Small",
                    "seed": seed,
                },
                checkpoint_path,
            )

    print(
        f"MM-SSNet Training Complete! "
        f"Best Val Accuracy: {best_val_acc:.2f}%. "
        f"Saved to "
        f"{os.path.join(CHECKPOINT_DIR, 'mmssnet.pth')}\n"
    )

    # ------------------------------------------------------------------
    # Reload the exact model state selected as the best validation
    # checkpoint before fitting OOD calibration.
    #
    # This guarantees that the Mahalanobis latent-space calibration
    # matches the deployed model.
    # ------------------------------------------------------------------
    checkpoint_path = os.path.join(
        CHECKPOINT_DIR,
        "mmssnet.pth",
    )

    checkpoint = torch.load(
        checkpoint_path,
        map_location=device,
        weights_only=False,
    )

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    model.eval()

    # Fit OOD calibration using the exact same model state
    # that is saved for deployment.
    calibrate_ood_detector(
        model,
        train_loader,
        device=device,
    )

    return model


def train_temporal_net(
    epochs=10,
    lr=1e-3,
    batch_size=32,
    dataset_type="SYNTHETIC_DEVELOPMENT_TEMPORAL_DATASET",
    manifest_path=None,
):
    """
    Trains TemporalStressNet model on chronological
    telemetry sequences.
    """

    print(
        f"=== Starting TemporalStressNet Training "
        f"({epochs} epochs, Dataset: {dataset_type}) ==="
    )

    os.makedirs(
        CHECKPOINT_DIR,
        exist_ok=True,
    )

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    if (
        dataset_type == "REAL_TEMPORAL_DATASET"
        and manifest_path
        and os.path.exists(manifest_path)
    ):
        ds = RealTemporalDataset(
            manifest_csv=manifest_path
        )
    else:
        x_seq, trends, fut_sevs = (
            generate_synthetic_temporal_data(
                num_samples=1000,
                seed=42,
            )
        )

        ds = SyntheticTemporalDataset(
            x_seq,
            trends,
            fut_sevs,
        )

    loader = DataLoader(
        ds,
        batch_size=batch_size,
        shuffle=True,
    )

    model = TemporalStressNet(
        in_features=15,
        hidden_dim=64,
        num_classes=4,
    ).to(device)

    optimizer = optim.Adam(
        model.parameters(),
        lr=lr,
    )

    cls_criterion = nn.CrossEntropyLoss()
    sev_criterion = nn.MSELoss()

    for epoch in range(
        1,
        epochs + 1,
    ):
        model.train()

        total_loss = 0.0
        correct = 0
        total = 0

        for batch in loader:
            x_b = batch["x_seq"].to(device)
            y_tr_b = batch["trend"].to(device)
            y_sev_b = batch["future_severity"].to(device)

            optimizer.zero_grad()

            out = model(x_b)

            loss_tr = cls_criterion(
                out["trend_logits"],
                y_tr_b,
            )

            loss_sev = sev_criterion(
                out["future_severity"],
                y_sev_b,
            )

            loss = (
                loss_tr
                + 0.01 * loss_sev
            )

            loss.backward()
            optimizer.step()

            total_loss += (
                loss.item()
                * len(y_tr_b)
            )

            preds = torch.argmax(
                out["trend_logits"],
                dim=1,
            )

            correct += (
                preds == y_tr_b
            ).sum().item()

            total += len(y_tr_b)

        acc = (
            correct / total
        ) * 100.0

        print(
            f"Temporal Epoch [{epoch:02d}/{epochs:02d}] - "
            f"Loss: {total_loss / total:.4f} | "
            f"Acc: {acc:.2f}%"
        )

    checkpoint_path = os.path.join(
        CHECKPOINT_DIR,
        "temporal_net.pth",
    )

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "dataset_type": dataset_type,
        },
        checkpoint_path,
    )

    print(
        f"TemporalStressNet Saved to "
        f"{checkpoint_path}\n"
    )

    return model


if __name__ == "__main__":
    train_mmssnet(
        epochs=10,
        seed=42,
    )

    train_temporal_net(
        epochs=10,
    )