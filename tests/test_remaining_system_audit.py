
"""
Final remaining-system audit for AgriSense.

Purpose:
- One test file for the remaining testable areas after the dedicated
  telemetry, fusion, geospatial, actuator, dataset-integrity, and
  reproducibility tests already completed.
- These tests intentionally test the production implementation.
- A failure is a finding; do NOT weaken the assertion just to make the
  suite pass.

Run:
    python -m pytest -q tests/test_remaining_system_audit.py
"""

import json
from pathlib import Path

import numpy as np
import pytest
import torch


# ---------------------------------------------------------------------------
# MM-SSNet structural / contract audit
# ---------------------------------------------------------------------------

def _make_model():
    from ml.model import MMSSNet

    model = MMSSNet(num_classes=6)
    model.eval()
    return model


def test_mmssnet_output_contract_with_all_modalities():
    model = _make_model()

    spectral = torch.randn(2, 10)
    spatial = torch.randn(2, 3, 64, 64)
    env = torch.randn(2, 4)

    with torch.no_grad():
        out = model(spectral, spatial, env)

    assert out["class_logits"].shape == (2, 6)
    assert out["severity"].shape == (2,)
    assert out["lead_time"].shape == (2,)
    assert out["latent_features"].shape == (2, 128)
    assert out["attn_weights"].shape == (2, 1, 1)
    assert out["spatial_modality_available"] is True

    for key in ("class_logits", "severity", "lead_time", "latent_features"):
        assert torch.isfinite(out[key]).all(), f"Non-finite values in {key}"

    assert torch.all(out["severity"] >= 0)
    assert torch.all(out["severity"] <= 100)
    assert torch.all(out["lead_time"] >= 0)


def test_mmssnet_missing_spatial_is_a_real_fallback():
    model = _make_model()

    spectral = torch.randn(2, 10)
    env = torch.randn(2, 4)

    with torch.no_grad():
        out = model(spectral, None, env)

    assert out["spatial_modality_available"] is False
    assert out["class_logits"].shape == (2, 6)
    assert out["latent_features"].shape == (2, 128)
    assert torch.allclose(
        out["attn_weights"],
        torch.zeros_like(out["attn_weights"]),
    )
    assert torch.isfinite(out["latent_features"]).all()


def test_mmssnet_missing_environment_uses_documented_default_path():
    model = _make_model()

    spectral = torch.randn(2, 10)

    with torch.no_grad():
        out = model(spectral, None, None)

    assert out["class_logits"].shape == (2, 6)
    assert out["severity"].shape == (2,)
    assert out["lead_time"].shape == (2,)
    assert torch.isfinite(out["latent_features"]).all()


def test_mmssnet_rejects_wrong_spectral_band_count():
    """
    AS7341 contract is 10 spectral bands. Adaptive pooling must not silently
    turn a 9- or 11-band input into a valid inference.
    """
    model = _make_model()

    with pytest.raises((RuntimeError, ValueError)):
        model(torch.randn(2, 9), None, torch.randn(2, 4))


def test_mmssnet_rejects_wrong_environment_feature_count():
    model = _make_model()

    with pytest.raises((RuntimeError, ValueError)):
        model(torch.randn(2, 10), None, torch.randn(2, 3))


def test_mmssnet_rejects_wrong_spatial_channel_count():
    model = _make_model()

    with pytest.raises((RuntimeError, ValueError)):
        model(torch.randn(2, 10), torch.randn(2, 1, 64, 64), torch.randn(2, 4))


def test_mmssnet_rejects_missing_spectral_stream():
    model = _make_model()

    with pytest.raises((AttributeError, RuntimeError, TypeError, ValueError)):
        model(None, None, torch.randn(2, 4))


def test_mmssnet_batch_size_mismatch_is_rejected():
    model = _make_model()

    with pytest.raises((RuntimeError, ValueError)):
        model(
            torch.randn(2, 10),
            torch.randn(3, 3, 64, 64),
            torch.randn(2, 4),
        )


# ---------------------------------------------------------------------------
# OOD / anomaly detector audit
# ---------------------------------------------------------------------------

def _make_calibrated_anomaly_service():
    from app.backend.services.anomaly_service import AnomalyDetectorService

    service = AnomalyDetectorService()
    service.is_calibrated = True
    service.latent_dim = 128
    service.mean_vector = np.zeros(128, dtype=np.float64)
    service.cov_inv = np.eye(128, dtype=np.float64)
    service.threshold = 5.0
    return service


def test_ood_in_distribution_vector_is_not_anomaly():
    service = _make_calibrated_anomaly_service()

    result = service.evaluate_ood(np.zeros(128), env_vec=[25, 60, 50, 80])

    assert result["is_calibrated"] is True
    assert result["is_anomaly"] is False
    assert result["classification"] == "IN_DISTRIBUTION"
    assert result["hardware_fault_detected"] is False


def test_ood_far_latent_vector_is_anomaly():
    service = _make_calibrated_anomaly_service()

    latent = np.zeros(128)
    latent[0] = 20.0

    result = service.evaluate_ood(latent, env_vec=[25, 60, 50, 80])

    assert result["is_anomaly"] is True
    assert result["classification"] == "UNKNOWN_ANOMALY"
    assert result["mahalanobis_distance"] > result["anomaly_threshold"]


def test_ood_invalid_latent_dimension_is_rejected():
    service = _make_calibrated_anomaly_service()

    with pytest.raises(ValueError):
        service.evaluate_ood(np.zeros(127))


def test_ood_none_latent_is_rejected():
    service = _make_calibrated_anomaly_service()

    with pytest.raises(ValueError):
        service.evaluate_ood(None)


@pytest.mark.parametrize(
    "env",
    [
        [-11.0, 60.0, 50.0, 80.0],
        [66.0, 60.0, 50.0, 80.0],
        [25.0, 60.0, -1.0, 80.0],
        [25.0, 60.0, 101.0, 80.0],
    ],
)
def test_ood_physical_sensor_bounds_trigger_hardware_fault(env):
    service = _make_calibrated_anomaly_service()

    result = service.evaluate_ood(np.zeros(128), env_vec=env)

    assert result["hardware_fault_detected"] is True
    assert result["is_anomaly"] is True
    assert result["anomaly_score"] == 99.9
    assert result["fault_reason"]


def test_ood_uncalibrated_detector_is_explicit():
    from app.backend.services.anomaly_service import AnomalyDetectorService

    service = AnomalyDetectorService()
    service.is_calibrated = False

    result = service.evaluate_ood(np.zeros(128))

    assert result["is_calibrated"] is False
    assert result["classification"] == "NOT_CALIBRATED"
    assert result["is_anomaly"] is False


# ---------------------------------------------------------------------------
# Temporal model / synthetic trajectory audit
# ---------------------------------------------------------------------------

def test_temporal_synthetic_generation_is_reproducible():
    from ml.temporal import generate_synthetic_temporal_data

    a = generate_synthetic_temporal_data(num_samples=40, seq_len=10, seed=42)
    b = generate_synthetic_temporal_data(num_samples=40, seq_len=10, seed=42)

    for xa, xb in zip(a, b):
        assert np.array_equal(xa, xb)


def test_temporal_synthetic_generation_changes_with_seed():
    from ml.temporal import generate_synthetic_temporal_data

    a = generate_synthetic_temporal_data(num_samples=40, seq_len=10, seed=42)
    b = generate_synthetic_temporal_data(num_samples=40, seq_len=10, seed=43)

    assert not np.array_equal(a[0], b[0])


def test_temporal_generation_output_contract():
    from ml.temporal import generate_synthetic_temporal_data

    x, trends, future_severity = generate_synthetic_temporal_data(
        num_samples=40,
        seq_len=10,
        seed=42,
    )

    assert x.shape == (40, 10, 15)
    assert trends.shape == (40,)
    assert future_severity.shape == (40,)
    assert set(np.unique(trends)).issubset({0, 1, 2, 3})
    assert np.isfinite(x).all()
    assert np.isfinite(future_severity).all()


def test_temporal_generation_does_not_drop_requested_remainder():
    """
    A generator must return exactly num_samples even when num_samples is not
    divisible by the four trajectory classes.
    """
    from ml.temporal import generate_synthetic_temporal_data

    x, trends, future_severity = generate_synthetic_temporal_data(
        num_samples=42,
        seq_len=10,
        seed=42,
    )

    assert len(x) == 42
    assert len(trends) == 42
    assert len(future_severity) == 42


def test_temporal_model_forward_contract():
    from ml.temporal import TemporalStressNet

    model = TemporalStressNet()
    model.eval()

    x = torch.randn(4, 10, 15)

    with torch.no_grad():
        out = model(x)

    assert out["trend_logits"].shape == (4, 4)
    assert out["future_severity"].shape == (4,)
    assert out["sequence_embeddings"].shape == (4, 64)

    assert torch.isfinite(out["trend_logits"]).all()
    assert torch.isfinite(out["future_severity"]).all()
    assert torch.isfinite(out["sequence_embeddings"]).all()
    assert torch.all(out["future_severity"] >= 0)
    assert torch.all(out["future_severity"] <= 100)


def test_temporal_model_rejects_wrong_feature_count():
    from ml.temporal import TemporalStressNet

    model = TemporalStressNet()

    with pytest.raises((RuntimeError, ValueError)):
        model(torch.randn(2, 10, 14))


# ---------------------------------------------------------------------------
# Ablation-study integrity audit
# ---------------------------------------------------------------------------

def test_ablation_has_exactly_seven_unique_variants():
    from ml.ablation import run_ablation_study

    captured = {}

    def fake_loader(data_manifest, dataset_type, batch_size, seed):
        captured.setdefault("loader_seeds", []).append(seed)
        return object(), object()

    def fake_train(cfg, train_loader, val_loader, epochs, device, seed):
        captured.setdefault("configs", []).append(dict(cfg))
        return {
            "seed": seed,
            "accuracy_pct": float(seed % 100),
            "precision_macro": 0.5,
            "recall_macro": 0.5,
            "f1_score_macro": 0.5,
            "f1_score_weighted": 0.5,
            "confusion_matrix": [[1]],
            "severity_rmse": 1.0,
            "lead_time_mae_hours": 2.0,
            "evaluation_dataset": "synthetic_development",
            "synthetic_development": True,
            "real_world_validation": False,
            "spectral_stream": cfg["use_spec"],
            "spatial_stream": cfg["use_spat"],
            "env_stream": cfg["use_env"],
        }

    import ml.ablation as ab

    original_loader = ab.get_dataloaders
    original_train = ab.train_and_evaluate_variant

    try:
        ab.get_dataloaders = fake_loader
        ab.train_and_evaluate_variant = fake_train
        ab.RESULTS_DIR = str(Path.cwd() / ".pytest_agrisense_results")

        result = run_ablation_study(
            epochs_per_variant=1,
            seeds=(42, 43),
            dataset_type="synthetic_development",
            manifest_path=None,
        )
    finally:
        ab.get_dataloaders = original_loader
        ab.train_and_evaluate_variant = original_train

    variants = result["variants"]

    assert len(variants) == 7
    assert len(set(variants.keys())) == 7

    expected = {
        "Variant A: Spatial RGB Only": (False, True, False),
        "Variant B: Spectral 1D Conv Only": (True, False, False),
        "Variant C: Environmental MLP Only": (False, False, True),
        "Variant D: Spatial RGB + Spectral 1D": (True, True, False),
        "Variant E: Spatial RGB + Environmental": (False, True, True),
        "Variant F: Spectral 1D + Environmental": (True, False, True),
        "Variant G: Tri-Modal MM-SSNet (Proposed)": (True, True, True),
    }

    for name, flags in expected.items():
        assert name in variants
        assert (
            variants[name]["spectral_stream"],
            variants[name]["spatial_stream"],
            variants[name]["env_stream"],
        ) == flags


def test_ablation_uses_same_dataset_seed_for_each_variant():
    import ml.ablation as ab

    calls = []

    def fake_loader(data_manifest, dataset_type, batch_size, seed):
        calls.append(seed)
        return object(), object()

    def fake_train(cfg, train_loader, val_loader, epochs, device, seed):
        return {
            "seed": seed,
            "accuracy_pct": 50.0,
            "precision_macro": 0.5,
            "recall_macro": 0.5,
            "f1_score_macro": 0.5,
            "f1_score_weighted": 0.5,
            "confusion_matrix": [[1]],
            "severity_rmse": 1.0,
            "lead_time_mae_hours": 2.0,
            "evaluation_dataset": "synthetic_development",
            "synthetic_development": True,
            "real_world_validation": False,
            "spectral_stream": cfg["use_spec"],
            "spatial_stream": cfg["use_spat"],
            "env_stream": cfg["use_env"],
        }

    original_loader = ab.get_dataloaders
    original_train = ab.train_and_evaluate_variant

    try:
        ab.get_dataloaders = fake_loader
        ab.train_and_evaluate_variant = fake_train
        ab.RESULTS_DIR = str(Path.cwd() / ".pytest_agrisense_results")

        ab.run_ablation_study(
            epochs_per_variant=1,
            seeds=(42, 43),
            dataset_type="synthetic_development",
            manifest_path=None,
        )
    finally:
        ab.get_dataloaders = original_loader
        ab.train_and_evaluate_variant = original_train

    assert calls == [42, 43] * 7


def test_ablation_aggregation_is_empirical_not_hardcoded():
    import ml.ablation as ab

    def fake_loader(data_manifest, dataset_type, batch_size, seed):
        return object(), object()

    def fake_train(cfg, train_loader, val_loader, epochs, device, seed):
        # Deliberately non-constant values so mean/std can be checked.
        acc = {42: 20.0, 43: 40.0}[seed]
        f1 = {42: 0.20, 43: 0.60}[seed]
        return {
            "seed": seed,
            "accuracy_pct": acc,
            "precision_macro": 0.5,
            "recall_macro": 0.5,
            "f1_score_macro": f1,
            "f1_score_weighted": f1,
            "confusion_matrix": [[1]],
            "severity_rmse": 1.0,
            "lead_time_mae_hours": 2.0,
            "evaluation_dataset": "synthetic_development",
            "synthetic_development": True,
            "real_world_validation": False,
            "spectral_stream": cfg["use_spec"],
            "spatial_stream": cfg["use_spat"],
            "env_stream": cfg["use_env"],
        }

    original_loader = ab.get_dataloaders
    original_train = ab.train_and_evaluate_variant

    try:
        ab.get_dataloaders = fake_loader
        ab.train_and_evaluate_variant = fake_train
        ab.RESULTS_DIR = str(Path.cwd() / ".pytest_agrisense_results")

        result = ab.run_ablation_study(
            epochs_per_variant=1,
            seeds=(42, 43),
            dataset_type="synthetic_development",
            manifest_path=None,
        )
    finally:
        ab.get_dataloaders = original_loader
        ab.train_and_evaluate_variant = original_train

    for variant in result["variants"].values():
        assert variant["accuracy_pct_mean"] == 30.0
        assert variant["accuracy_pct_std"] == 10.0
        assert variant["f1_score_macro_mean"] == 0.4
        assert variant["f1_score_macro_std"] == 0.2

        assert [m["seed"] for m in variant["seed_runs"]] == [42, 43]


def test_ablation_report_is_explicitly_synthetic():
    report_path = Path("ml/results/ablation_report.json")

    if not report_path.exists():
        pytest.skip("No generated ablation_report.json is present in this checkout.")

    data = json.loads(report_path.read_text(encoding="utf-8"))

    assert data["metadata"]["dataset_type"] == "synthetic_development"
    assert data["metadata"]["real_world_validation"] is False
    assert data["metadata"]["deterministic_training"] is True

    for variant in data["variants"].values():
        assert variant["synthetic_development"] is True
        assert variant["real_world_validation"] is False
        assert len(variant["seed_runs"]) == data["metadata"]["num_seeds"]


# ---------------------------------------------------------------------------
# Dataset / checkpoint metadata safety audit
# ---------------------------------------------------------------------------

def test_project_ml_metadata_does_not_claim_real_world_validation():
    config_path = Path("ml/synthetic_config.yaml")

    if not config_path.exists():
        pytest.fail("ml/synthetic_config.yaml not found")

    source = config_path.read_text(encoding="utf-8").lower()

    # The configuration must explicitly identify itself as development/
    # simulation data and must not claim real-world validation.
    assert "synthetic" in source
    assert "simulation" in source

    # Guard against an explicit positive real-world-validation claim.
    assert "real_world_validation: true" not in source
    assert "real-world validation: true" not in source


def test_temporal_checkpoint_if_present_is_marked_synthetic():
    checkpoint = Path("ml/checkpoints/temporal_net.pth")

    if not checkpoint.exists():
        pytest.skip("Temporal checkpoint is not present in this checkout.")

    data = torch.load(checkpoint, map_location="cpu")

    assert data["dataset_type"] == "synthetic_development"
    assert data["real_world_validation"] is False
    assert "model_state_dict" in data
    assert "seed" in data


def test_ood_calibration_if_present_has_128_dimensional_parameters():
    calibration = Path("ml/checkpoints/ood_calibration.json")

    if not calibration.exists():
        pytest.skip("OOD calibration file is not present in this checkout.")

    data = json.loads(calibration.read_text(encoding="utf-8"))

    if not data.get("is_calibrated", False):
        pytest.skip("OOD calibration file exists but is explicitly uncalibrated.")

    mean = np.asarray(data["mean_vector"])
    cov_inv = np.asarray(data["cov_inv"])

    assert mean.shape == (128,)
    assert cov_inv.shape == (128, 128)
    assert np.isfinite(mean).all()
    assert np.isfinite(cov_inv).all()
    assert float(data["threshold"]) > 0


# ---------------------------------------------------------------------------
# Static telemetry safety audit (does not replace the existing API runtime
# test; it catches accidental regression in the real-vs-simulation boundary).
# ---------------------------------------------------------------------------

def test_telemetry_router_contains_real_hardware_boundary():
    telemetry_path = Path("app/backend/routers/telemetry.py")

    if not telemetry_path.exists():
        pytest.fail("Telemetry router not found at app/backend/routers/telemetry.py")

    source = telemetry_path.read_text(encoding="utf-8")

    assert 'latest_telemetry.is_real_hardware = True' in source
    assert 'latest_telemetry.is_real_hardware = False' in source
    assert 'ai_service.predict(' in source
    assert 'fusion_service.disambiguate_stress(' in source
    assert 'anomaly_service.evaluate_ood(' in source
    assert '"is_real_ai": True' in source
    assert '"recommended_action"' in source
    assert '"rule_type"' in source
    assert '"REAL_ESP32 -> PYTORCH_MMSSNET -> FUSION -> OOD -> WEBSOCKET"' in source


def test_telemetry_simulation_route_is_explicitly_tagged():
    telemetry_path = Path("app/backend/routers/telemetry.py")
    source = telemetry_path.read_text(encoding="utf-8")

    assert '"mode": "SIMULATION"' in source
    assert '"pipeline": "SIL_SIMULATION_MODE"' in source
    assert 'latest_telemetry.is_real_hardware = False' in source
