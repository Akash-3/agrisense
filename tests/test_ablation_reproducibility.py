import json
import os

import ml.ablation as ablation_module


def test_ablation_same_seed_is_reproducible(tmp_path, monkeypatch):
    """
    The same ablation experiment and seed should produce the
    same metrics when executed twice.
    """

    monkeypatch.setattr(
        ablation_module,
        "RESULTS_DIR",
        str(tmp_path),
    )

    # Run the experiment once.
    result_1 = ablation_module.run_ablation_study(
        seeds=[42],
    )

    # Run it again with exactly the same seed.
    result_2 = ablation_module.run_ablation_study(
        seeds=[42],
    )

    assert result_1 == result_2


def test_ablation_different_seed_changes_results(tmp_path, monkeypatch):
    """
    Different experiment seeds should not produce identical
    ablation results.
    """

    monkeypatch.setattr(
        ablation_module,
        "RESULTS_DIR",
        str(tmp_path),
    )

    result_1 = ablation_module.run_ablation_study(
        seeds=[42],
    )

    result_2 = ablation_module.run_ablation_study(
        seeds=[123],
    )

    assert result_1 != result_2