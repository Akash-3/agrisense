import os
import torch

from ml.model import MMSSNet


def test_saved_checkpoint_matches_best_epoch_metadata():
    checkpoint_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "ml",
            "checkpoints",
            "mmssnet.pth",
        )
    )

    assert os.path.exists(
        checkpoint_path
    ), "MM-SSNet checkpoint does not exist"

    checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )

    assert "model_state_dict" in checkpoint
    assert "epoch" in checkpoint
    assert "val_acc" in checkpoint

    assert checkpoint["epoch"] >= 1
    assert checkpoint["val_acc"] >= 0.0
    assert checkpoint["val_acc"] <= 100.0


def test_ood_calibration_exists_and_matches_latent_dimension():
    calibration_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "ml",
            "checkpoints",
            "ood_calibration.json",
        )
    )

    assert os.path.exists(
        calibration_path
    ), "OOD calibration file does not exist"

    import json

    with open(calibration_path, "r") as f:
        calibration = json.load(f)

    assert calibration["is_calibrated"] is True
    assert calibration["latent_dim"] == 128
    assert calibration["num_calibration_samples"] > 0

    assert len(calibration["mean_vector"]) == 128
    assert len(calibration["cov_inv"]) == 128
    assert all(len(row) == 128 for row in calibration["cov_inv"])

    assert calibration["threshold"] > 0.0