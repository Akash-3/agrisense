import torch
import ml.train as train_module


def test_ood_calibration_uses_saved_best_checkpoint(monkeypatch, tmp_path):
    saved_state = None
    calibration_state = None

    # Keep the real torch.save() before monkeypatching it.
    original_torch_save = torch.save

    class FakeModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(1.0))
            self.forward_calls = 0

        def forward(self, spec, spat, env):
            self.forward_calls += 1
            batch_size = spec.shape[0]

            logits = torch.zeros(batch_size, 6)

            # Epoch 1:
            #   training forward = call 1
            #   validation forward = call 2
            #   validation predicts class 0 -> 100% accuracy
            #
            # Epoch 2:
            #   training forward = call 3
            #   validation forward = call 4
            #   validation predicts class 1 -> 0% accuracy
            #
            # Therefore epoch 1 is the best checkpoint while epoch 2
            # leaves the model in a different final state.
            if self.forward_calls == 2:
                logits[:, 0] = 10.0
            elif self.forward_calls == 4:
                logits[:, 1] = 10.0
            else:
                logits[:, 0] = self.weight

            return {
                "class_logits": logits,
                "severity": torch.zeros(batch_size),
                "lead_time": torch.zeros(batch_size),
                "latent_features": self.weight.expand(
                    batch_size,
                    128,
                ).clone(),
            }

    class FakeLoader:
        def __init__(self):
            self.batch = {
                "spectral": torch.zeros(4, 10),
                "spatial": torch.zeros(4, 3, 64, 64),
                "env": torch.zeros(4, 4),
                "label": torch.zeros(4, dtype=torch.long),
                "severity": torch.zeros(4),
                "lead_time": torch.zeros(4),
            }

        def __iter__(self):
            yield self.batch

        def __len__(self):
            return 1

    def fake_save(obj, path):
        nonlocal saved_state

        if str(path).endswith("mmssnet.pth"):
            saved_state = {
                k: v.detach().cpu().clone()
                for k, v in obj["model_state_dict"].items()
            }

        # Actually write the checkpoint so the production reload
        # can execute.
        original_torch_save(obj, path)

    def fake_calibrate(model, train_loader, device="cpu"):
        nonlocal calibration_state

        calibration_state = {
            k: v.detach().cpu().clone()
            for k, v in model.state_dict().items()
        }

        return {
            "is_calibrated": True,
            "latent_dim": 128,
            "num_calibration_samples": 4,
            "threshold": 1.0,
        }

    # Replace the real MMSSNet with the controlled test model.
    monkeypatch.setattr(
        train_module,
        "MMSSNet",
        lambda num_classes=6: FakeModel(),
    )

    # Replace the real dataloaders with deterministic tiny loaders.
    monkeypatch.setattr(
        train_module,
        "get_dataloaders",
        lambda **kwargs: (
            FakeLoader(),
            FakeLoader(),
        ),
    )

    # Capture the checkpoint while still allowing it to be written.
    monkeypatch.setattr(
        train_module.torch,
        "save",
        fake_save,
    )

    # Capture the exact model state supplied to OOD calibration.
    monkeypatch.setattr(
        train_module,
        "calibrate_ood_detector",
        fake_calibrate,
    )

    # Keep all test artifacts inside pytest's temporary directory.
    train_module.CHECKPOINT_DIR = str(tmp_path)

    train_module.train_mmssnet(
        epochs=2,
        lr=1e-3,
        batch_size=4,
        dataset_type="SYNTHETIC_DEVELOPMENT_DATASET",
    )

    assert saved_state is not None, (
        "No best MM-SSNet checkpoint was saved."
    )

    assert calibration_state is not None, (
        "OOD calibration was never called."
    )

    # OOD calibration must use the exact same model state
    # that was selected as the best validation checkpoint.
    for key in saved_state:
        assert torch.equal(
            saved_state[key],
            calibration_state[key],
        ), (
            "OOD calibration used a different model state than "
            f"the saved best checkpoint for parameter: {key}"
        )