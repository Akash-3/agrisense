import os
import torch

import ml.train as train_module


def _state_dict_equal(state_a, state_b):
    assert state_a.keys() == state_b.keys()

    for key in state_a:
        assert torch.equal(
            state_a[key],
            state_b[key],
        ), f"Mismatch in parameter: {key}"


def test_same_seed_produces_identical_training_checkpoint(tmp_path, monkeypatch):
    """
    Two complete MM-SSNet training runs with the same seed must
    produce identical model weights and validation metrics.
    """

    monkeypatch.setattr(
        train_module,
        "CHECKPOINT_DIR",
        str(tmp_path),
    )

    train_module.train_mmssnet(
        epochs=1,
        batch_size=32,
        seed=42,
    )

    checkpoint_path = os.path.join(
        tmp_path,
        "mmssnet.pth",
    )

    first_checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )

    first_state = {
        key: value.clone()
        for key, value in first_checkpoint["model_state_dict"].items()
    }

    first_val_acc = first_checkpoint["val_acc"]

    # Run the complete training process again with the SAME seed.
    train_module.train_mmssnet(
        epochs=1,
        batch_size=32,
        seed=42,
    )

    second_checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )

    second_state = second_checkpoint["model_state_dict"]
    second_val_acc = second_checkpoint["val_acc"]

    _state_dict_equal(
        first_state,
        second_state,
    )

    assert first_val_acc == second_val_acc


def test_different_seed_changes_training_checkpoint(tmp_path, monkeypatch):
    """
    Different seeds should produce different model initialization/
    training outcomes.
    """

    monkeypatch.setattr(
        train_module,
        "CHECKPOINT_DIR",
        str(tmp_path),
    )

    train_module.train_mmssnet(
        epochs=1,
        batch_size=32,
        seed=42,
    )

    checkpoint_path = os.path.join(
        tmp_path,
        "mmssnet.pth",
    )

    first_checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )

    first_state = first_checkpoint["model_state_dict"]

    train_module.train_mmssnet(
        epochs=1,
        batch_size=32,
        seed=123,
    )

    second_checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )

    second_state = second_checkpoint["model_state_dict"]

    identical = all(
        torch.equal(
            first_state[key],
            second_state[key],
        )
        for key in first_state
    )

    assert not identical