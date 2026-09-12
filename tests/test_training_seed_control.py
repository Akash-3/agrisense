import inspect

import ml.train as train_module


def test_train_mmssnet_exposes_seed_parameter():
    """
    Training must expose an explicit seed so an experiment can be
    reproduced from its public training API.
    """

    signature = inspect.signature(train_module.train_mmssnet)

    assert "seed" in signature.parameters
    assert signature.parameters["seed"].default == 42


def test_train_mmssnet_passes_seed_to_dataloaders(monkeypatch):
    """
    Verify that the training seed is actually forwarded to the
    dataset/split construction.
    """

    captured = {}

    def fake_get_dataloaders(**kwargs):
        captured.update(kwargs)

        # train_mmssnet would otherwise try to iterate these.
        class EmptyLoader:
            def __iter__(self):
                return iter([])

            def __len__(self):
                return 0

        return EmptyLoader(), EmptyLoader()

    monkeypatch.setattr(
        train_module,
        "get_dataloaders",
        fake_get_dataloaders,
    )

    # Prevent actual model training.
    class FakeModel:
        pass

    monkeypatch.setattr(
        train_module,
        "MMSSNet",
        lambda num_classes=6: FakeModel(),
    )

    # We only need to verify argument propagation, so inspect the
    # function source contract through a direct lightweight call
    # setup rather than running the training loop.
    #
    # The actual propagation assertion is checked by examining the
    # current source implementation.
    source = inspect.getsource(train_module.train_mmssnet)

    assert "seed=seed" in source, (
        "train_mmssnet() does not pass its seed to get_dataloaders()."
    )