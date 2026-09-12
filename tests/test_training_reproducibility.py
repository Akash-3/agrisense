import torch
import numpy as np

import ml.train as train_module


def test_same_seed_produces_same_model_initialization(monkeypatch):
    """
    Verify whether explicitly setting the same RNG state produces
    identical MM-SSNet initialization.
    """

    torch.manual_seed(42)
    np.random.seed(42)

    model_a = train_module.MMSSNet(num_classes=6)

    state_a = {
        k: v.detach().cpu().clone()
        for k, v in model_a.state_dict().items()
    }

    torch.manual_seed(42)
    np.random.seed(42)

    model_b = train_module.MMSSNet(num_classes=6)

    state_b = {
        k: v.detach().cpu().clone()
        for k, v in model_b.state_dict().items()
    }

    for key in state_a:
        assert torch.equal(
            state_a[key],
            state_b[key],
        ), f"Model initialization differs for parameter: {key}"


def test_different_seed_produces_different_model_initialization():
    """
    Different RNG seeds should normally produce different model
    initialization.
    """

    torch.manual_seed(42)
    np.random.seed(42)

    model_a = train_module.MMSSNet(num_classes=6)

    torch.manual_seed(43)
    np.random.seed(43)

    model_b = train_module.MMSSNet(num_classes=6)

    differences = []

    for key in model_a.state_dict():
        if not torch.equal(
            model_a.state_dict()[key],
            model_b.state_dict()[key],
        ):
            differences.append(key)

    assert differences, (
        "Different seeds unexpectedly produced identical "
        "model initialization."
    )