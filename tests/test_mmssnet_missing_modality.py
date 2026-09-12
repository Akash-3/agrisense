import torch

from ml.model import MMSSNet


def test_model_runs_without_spatial_modality():
    torch.manual_seed(42)

    model = MMSSNet(num_classes=6)
    model.eval()

    spectral = torch.randn(2, 10)
    env = torch.randn(2, 4)

    with torch.no_grad():
        output = model(
            spectral,
            None,
            env,
        )

    assert "class_logits" in output
    assert "severity" in output
    assert "lead_time" in output
    assert "latent_features" in output
    assert "spatial_modality_available" in output

    assert output["class_logits"].shape == (2, 6)
    assert output["severity"].shape == (2,)
    assert output["lead_time"].shape == (2,)
    assert output["latent_features"].shape == (2, 128)

    assert output["spatial_modality_available"] is False


def test_model_runs_with_spatial_modality():
    torch.manual_seed(42)

    model = MMSSNet(num_classes=6)
    model.eval()

    spectral = torch.randn(2, 10)
    spatial = torch.randn(2, 3, 64, 64)
    env = torch.randn(2, 4)

    with torch.no_grad():
        output = model(
            spectral,
            spatial,
            env,
        )

    assert output["class_logits"].shape == (2, 6)
    assert output["severity"].shape == (2,)
    assert output["lead_time"].shape == (2,)
    assert output["latent_features"].shape == (2, 128)

    assert output["spatial_modality_available"] is True


def test_missing_spatial_does_not_produce_nan_or_inf():
    torch.manual_seed(42)

    model = MMSSNet(num_classes=6)
    model.eval()

    spectral = torch.randn(2, 10)
    env = torch.randn(2, 4)

    with torch.no_grad():
        output = model(
            spectral,
            None,
            env,
        )

    for key in [
        "class_logits",
        "severity",
        "lead_time",
        "latent_features",
    ]:
        assert torch.isfinite(
            output[key]
        ).all(), f"{key} contains NaN or Inf"