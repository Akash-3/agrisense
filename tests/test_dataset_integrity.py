import numpy as np

from ml.dataset import (
    generate_synthetic_multimodal_data,
    get_dataloaders,
)


def test_synthetic_dataset_has_expected_size_and_all_classes():
    data = generate_synthetic_multimodal_data(
        num_samples=1000,
        seed=42,
    )

    # Current production function returns 7 arrays.
    assert len(data) == 7

    spectral, spatial, env, labels, severity, lead_time, _ = data

    expected = 1000

    assert len(spectral) == expected
    assert len(spatial) == expected
    assert len(env) == expected
    assert len(labels) == expected
    assert len(severity) == expected
    assert len(lead_time) == expected

    class_counts = np.bincount(labels.astype(int), minlength=6)

    assert len(class_counts) == 6
    assert np.all(class_counts > 0), (
        f"Missing classes in synthetic dataset: {class_counts}"
    )


def test_synthetic_generation_is_reproducible_for_same_seed():
    data_a = generate_synthetic_multimodal_data(
        num_samples=180,
        seed=42,
    )

    data_b = generate_synthetic_multimodal_data(
        num_samples=180,
        seed=42,
    )

    assert len(data_a) == len(data_b) == 7

    for a, b in zip(data_a, data_b):
        np.testing.assert_array_equal(a, b)


def test_synthetic_generation_changes_with_different_seed():
    data_a = generate_synthetic_multimodal_data(
        num_samples=180,
        seed=42,
    )

    data_b = generate_synthetic_multimodal_data(
        num_samples=180,
        seed=43,
    )

    spectral_a = data_a[0]
    spectral_b = data_b[0]

    assert not np.array_equal(spectral_a, spectral_b)


def test_train_validation_split_is_complete_and_disjoint():
    train_loader, val_loader = get_dataloaders(
        batch_size=32,
        train_ratio=0.8,
        seed=42,
        dataset_type="synthetic_development",
    )

    train_ds = train_loader.dataset
    val_ds = val_loader.dataset

    assert len(train_ds) + len(val_ds) == 1800
    assert len(train_ds) == 1440
    assert len(val_ds) == 360

    # Recreate the exact deterministic synthetic dataset.
    (
        spectral,
        spatial,
        env,
        labels,
        severity,
        lead_time,
        _,
    ) = generate_synthetic_multimodal_data(
        num_samples=1800,
        seed=42,
    )

    # Recreate the deterministic 80/20 split used by production code.
    indices = np.arange(1800)

    rng = np.random.RandomState(42)
    rng.shuffle(indices)

    train_size = int(0.8 * 1800)

    expected_train_idx = indices[:train_size]
    expected_val_idx = indices[train_size:]

    # Verify that production train data corresponds exactly to
    # the expected training partition.
    np.testing.assert_array_equal(
        train_ds.spectral.numpy(),
        spectral[expected_train_idx],
    )

    # Verify that production validation data corresponds exactly
    # to the expected validation partition.
    np.testing.assert_array_equal(
        val_ds.spectral.numpy(),
        spectral[expected_val_idx],
    )

    # Explicit partition integrity checks.
    assert len(set(expected_train_idx) & set(expected_val_idx)) == 0
    assert len(set(expected_train_idx) | set(expected_val_idx)) == 1800


def test_synthetic_dataset_metadata_is_honest():
    train_loader, val_loader = get_dataloaders(
        batch_size=32,
        train_ratio=0.8,
        seed=42,
        dataset_type="synthetic_development",
    )

    train_ds = train_loader.dataset
    val_ds = val_loader.dataset

    assert train_ds.dataset_type == "synthetic_development"
    assert val_ds.dataset_type == "synthetic_development"

    assert train_ds.real_world_validation is False
    assert val_ds.real_world_validation is False