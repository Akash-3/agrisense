import torch

import ml.ablation as ablation_module


def test_ablation_variant_modality_flags_are_respected(monkeypatch):
    """
    Verify that train_and_evaluate_variant constructs the intended
    modality inputs for each ablation configuration.
    """

    captured = []

    class FakeOutput:
        def __init__(self, batch_size):
            self.class_logits = torch.zeros(
                batch_size,
                6,
            )
            self.severity = torch.zeros(
                batch_size,
            )
            self.lead_time = torch.zeros(
                batch_size,
            )

    class FakeModel(torch.nn.Module):
        def __init__(self, num_classes=6):
            super().__init__()
            self.dummy = torch.nn.Parameter(
                torch.tensor(1.0)
            )

        def forward(self, spec, spat, env):
            captured.append(
                {
                    "spectral": spec.detach().clone(),
                    "spatial": (
                        None
                        if spat is None
                        else spat.detach().clone()
                    ),
                    "env": env.detach().clone(),
                }
            )

            batch_size = spec.shape[0]

            class_logits = (
                torch.zeros(
                    batch_size,
                    6,
                    device=spec.device,
                )
                + self.dummy
            )

            severity = (
                torch.zeros(
                    batch_size,
                    device=spec.device,
                )
                + self.dummy
            )

            lead_time = (
                torch.zeros(
                    batch_size,
                    device=spec.device,
                )
                + self.dummy
            )

            return {
                "class_logits": class_logits,
                "severity": severity,
                "lead_time": lead_time,
            }
    monkeypatch.setattr(
        ablation_module,
        "MMSSNet",
        FakeModel,
    )

    batch = {
        "spectral": torch.ones(2, 10),
        "spatial": torch.ones(2, 3, 8, 8),
        "env": torch.ones(2, 4),
        "label": torch.tensor([0, 1]),
        "severity": torch.zeros(2),
        "lead_time": torch.zeros(2),
    }

    class SingleBatchLoader:
        def __iter__(self):
            return iter([batch])

        def __len__(self):
            return 1

    loader = SingleBatchLoader()

    variants = [
        {
            "name": "Spatial only",
            "use_spec": False,
            "use_spat": True,
            "use_env": False,
        },
        {
            "name": "Spectral only",
            "use_spec": True,
            "use_spat": False,
            "use_env": False,
        },
        {
            "name": "Environment only",
            "use_spec": False,
            "use_spat": False,
            "use_env": True,
        },
        {
            "name": "All modalities",
            "use_spec": True,
            "use_spat": True,
            "use_env": True,
        },
    ]

    for variant in variants:
        captured.clear()

        ablation_module.train_and_evaluate_variant(
            variant,
            loader,
            loader,
            epochs=1,
            device="cpu",
            seed=42,
        )

        assert captured, (
            f"No model forward pass captured for {variant['name']}"
        )

        first_call = captured[0]

        if variant["use_spec"]:
            assert torch.all(
                first_call["spectral"] == 1
            )
        else:
            assert torch.all(
                first_call["spectral"] == 0
            )

        if variant["use_spat"]:
            assert first_call["spatial"] is not None
            assert torch.all(
                first_call["spatial"] == 1
            )
        else:
            assert first_call["spatial"] is None

        if variant["use_env"]:
            assert torch.all(
                first_call["env"] == 1
            )
        else:
            assert torch.all(
                first_call["env"] == 0
            )