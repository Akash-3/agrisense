import torch

from ml.model import MMSSNet


def _make_inputs():
    torch.manual_seed(42)

    spectral = torch.randn(1, 10)
    spatial = torch.randn(1, 3, 64, 64)
    env = torch.randn(1, 4)

    return spectral, spatial, env


def _get_logits(model, spectral, spatial, env):
    with torch.no_grad():
        output = model(
            spectral,
            spatial,
            env,
        )

    return output["class_logits"].detach().cpu()


def test_spectral_modality_influences_output():
    model = MMSSNet(num_classes=6)
    model.eval()

    spectral, spatial, env = _make_inputs()

    baseline = _get_logits(
        model,
        spectral,
        spatial,
        env,
    )

    changed_spectral = spectral.clone()
    changed_spectral[0, 0] += 1.0

    changed = _get_logits(
        model,
        changed_spectral,
        spatial,
        env,
    )

    assert not torch.equal(
        baseline,
        changed,
    ), "Changing spectral input did not change model output"


def test_spatial_modality_influences_output():
    model = MMSSNet(num_classes=6)
    model.eval()

    spectral, spatial, env = _make_inputs()

    baseline = _get_logits(
        model,
        spectral,
        spatial,
        env,
    )

    changed_spatial = spatial.clone()
    changed_spatial[0, :, 10:20, 10:20] += 1.0

    changed = _get_logits(
        model,
        spectral,
        changed_spatial,
        env,
    )

    assert not torch.equal(
        baseline,
        changed,
    ), "Changing spatial input did not change model output"


def test_environmental_modality_influences_output():
    model = MMSSNet(num_classes=6)
    model.eval()

    spectral, spatial, env = _make_inputs()

    baseline = _get_logits(
        model,
        spectral,
        spatial,
        env,
    )

    changed_env = env.clone()
    changed_env[0, 0] += 1.0

    changed = _get_logits(
        model,
        spectral,
        spatial,
        changed_env,
    )

    assert not torch.equal(
        baseline,
        changed,
    ), "Changing environmental input did not change model output"