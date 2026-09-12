import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    mean_squared_error,
    mean_absolute_error,
    confusion_matrix,
)

from ml.dataset import get_dataloaders
from ml.model import MMSSNet


RESULTS_DIR = os.path.join(
    os.path.dirname(__file__),
    "results",
)


def train_and_evaluate_variant(
    variant_cfg,
    train_loader,
    val_loader,
    epochs=3,
    device="cpu",
    seed=42,
):
    """
    Trains and dynamically evaluates a model ablation variant
    on held-out validation data.

    NO HARDCODED NUMBERS ARE USED. All metrics are calculated
    from actual PyTorch model predictions.

    Reproducibility is controlled independently for every
    (variant, seed) experiment.
    """

    # --------------------------------------------------------------
    # Reproducibility / experiment seed
    # --------------------------------------------------------------
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    # Force deterministic CUDA/cuDNN behavior.
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)

    # --------------------------------------------------------------
    # Model
    # --------------------------------------------------------------
    model = MMSSNet(
        num_classes=6
    ).to(device)

    optimizer = optim.Adam(
        model.parameters(),
        lr=1e-3,
    )

    cls_criterion = nn.CrossEntropyLoss()
    sev_criterion = nn.MSELoss()
    lead_criterion = nn.MSELoss()

    use_spec = variant_cfg["use_spec"]
    use_spat = variant_cfg["use_spat"]
    use_env = variant_cfg["use_env"]

    # --------------------------------------------------------------
    # Training Loop
    # --------------------------------------------------------------
    for epoch in range(
        1,
        epochs + 1,
    ):
        model.train()

        for batch in train_loader:
            spec = (
                batch["spectral"].to(device)
                if use_spec
                else torch.zeros_like(
                    batch["spectral"]
                ).to(device)
            )

            spat = (
                batch["spatial"].to(device)
                if use_spat
                else None
            )

            env = (
                batch["env"].to(device)
                if use_env
                else torch.zeros_like(
                    batch["env"]
                ).to(device)
            )

            target_cls = batch["label"].to(device)
            target_sev = batch["severity"].to(device)
            target_lead = batch["lead_time"].to(device)

            optimizer.zero_grad()

            out = model(
                spec,
                spat,
                env,
            )

            l_cls = cls_criterion(
                out["class_logits"],
                target_cls,
            )

            l_sev = sev_criterion(
                out["severity"],
                target_sev,
            )

            l_lead = lead_criterion(
                out["lead_time"],
                target_lead,
            )

            loss = (
                l_cls
                + 0.01 * l_sev
                + 0.005 * l_lead
            )

            loss.backward()
            optimizer.step()

    # --------------------------------------------------------------
    # Evaluation on held-out validation split
    # --------------------------------------------------------------
    model.eval()

    all_preds = []
    all_targets = []

    all_sev_preds = []
    all_sev_targets = []

    all_lead_preds = []
    all_lead_targets = []

    dataset_type_label = "synthetic_development"

    with torch.no_grad():
        for batch in val_loader:
            spec = (
                batch["spectral"].to(device)
                if use_spec
                else torch.zeros_like(
                    batch["spectral"]
                ).to(device)
            )

            spat = (
                batch["spatial"].to(device)
                if use_spat
                else None
            )

            env = (
                batch["env"].to(device)
                if use_env
                else torch.zeros_like(
                    batch["env"]
                ).to(device)
            )

            target_cls = batch["label"].to(device)
            target_sev = batch["severity"].to(device)
            target_lead = batch["lead_time"].to(device)

            out = model(
                spec,
                spat,
                env,
            )

            preds = torch.argmax(
                out["class_logits"],
                dim=1,
            )

            all_preds.extend(
                preds.cpu().numpy()
            )

            all_targets.extend(
                target_cls.cpu().numpy()
            )

            all_sev_preds.extend(
                out["severity"].cpu().numpy()
            )

            all_sev_targets.extend(
                target_sev.cpu().numpy()
            )

            all_lead_preds.extend(
                out["lead_time"].cpu().numpy()
            )

            all_lead_targets.extend(
                target_lead.cpu().numpy()
            )

            if "dataset_type" in batch:
                dataset_type_label = (
                    batch["dataset_type"][0]
                    if isinstance(
                        batch["dataset_type"],
                        (list, tuple),
                    )
                    else batch["dataset_type"]
                )

    # --------------------------------------------------------------
    # Calculate actual empirical metrics
    # --------------------------------------------------------------
    acc = float(
        accuracy_score(
            all_targets,
            all_preds,
        )
        * 100.0
    )

    prec = float(
        precision_score(
            all_targets,
            all_preds,
            average="macro",
            zero_division=0,
        )
    )

    rec = float(
        recall_score(
            all_targets,
            all_preds,
            average="macro",
            zero_division=0,
        )
    )

    f1_macro = float(
        f1_score(
            all_targets,
            all_preds,
            average="macro",
            zero_division=0,
        )
    )

    f1_weighted = float(
        f1_score(
            all_targets,
            all_preds,
            average="weighted",
            zero_division=0,
        )
    )

    cm = confusion_matrix(
        all_targets,
        all_preds,
    ).tolist()

    sev_rmse = float(
        np.sqrt(
            mean_squared_error(
                all_sev_targets,
                all_sev_preds,
            )
        )
    )

    lead_mae = float(
        mean_absolute_error(
            all_lead_targets,
            all_lead_preds,
        )
    )

    return {
        "seed": int(seed),
        "accuracy_pct": round(acc, 2),
        "precision_macro": round(prec, 4),
        "recall_macro": round(rec, 4),
        "f1_score_macro": round(f1_macro, 4),
        "f1_score_weighted": round(
            f1_weighted,
            4,
        ),
        "confusion_matrix": cm,
        "severity_rmse": round(
            sev_rmse,
            4,
        ),
        "lead_time_mae_hours": round(
            lead_mae,
            4,
        ),
        "evaluation_dataset": dataset_type_label,
        "synthetic_development": True,
        "real_world_validation": False,
        "spectral_stream": use_spec,
        "spatial_stream": use_spat,
        "env_stream": use_env,
    }


def run_ablation_study(
    epochs_per_variant=2,
    seeds=(42, 43, 44),
    dataset_type="synthetic_development",
    manifest_path=None,
):
    """
    Executes dynamic multi-seed ablation benchmark comparison
    across all 7 modality combinations.

    NO METRICS ARE HARDCODED. All values are calculated from
    PyTorch model forward passes and ground-truth targets.

    Calculates mean ± std across the supplied random seeds.
    """

    os.makedirs(
        RESULTS_DIR,
        exist_ok=True,
    )

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(
        "=== Starting AgriSense 2.0 Dynamic "
        f"7-Variant Multi-Seed Ablation Study "
        f"({dataset_type}) ==="
    )

    # --------------------------------------------------------------
    # Seven ablation configurations
    # --------------------------------------------------------------
    ablation_configs = [
        {
            "name": "Variant A: Spatial RGB Only",
            "use_spec": False,
            "use_spat": True,
            "use_env": False,
        },
        {
            "name": "Variant B: Spectral 1D Conv Only",
            "use_spec": True,
            "use_spat": False,
            "use_env": False,
        },
        {
            "name": "Variant C: Environmental MLP Only",
            "use_spec": False,
            "use_spat": False,
            "use_env": True,
        },
        {
            "name": "Variant D: Spatial RGB + Spectral 1D",
            "use_spec": True,
            "use_spat": True,
            "use_env": False,
        },
        {
            "name": "Variant E: Spatial RGB + Environmental",
            "use_spec": False,
            "use_spat": True,
            "use_env": True,
        },
        {
            "name": "Variant F: Spectral 1D + Environmental",
            "use_spec": True,
            "use_spat": False,
            "use_env": True,
        },
        {
            "name": "Variant G: Tri-Modal MM-SSNet (Proposed)",
            "use_spec": True,
            "use_spat": True,
            "use_env": True,
        },
    ]

    results = {
        "metadata": {
            "num_variants": 7,
            "seeds_evaluated": list(seeds),
            "num_seeds": len(seeds),
            "dataset_type": "synthetic_development",
            "real_world_validation": False,
            "epochs_per_variant": epochs_per_variant,
            "deterministic_training": True,
        },
        "variants": {},
    }

    # --------------------------------------------------------------
    # Run each ablation variant for each seed
    # --------------------------------------------------------------
    for cfg in ablation_configs:
        name = cfg["name"]

        seed_metrics = []

        print(
            f"\nTraining & Evaluating {name} "
            f"across seeds {seeds}..."
        )

        for seed in seeds:
            # Dataset generation and train/validation split
            # are controlled by the same experiment seed.
            train_loader, val_loader = get_dataloaders(
                data_manifest=manifest_path,
                dataset_type=dataset_type,
                batch_size=32,
                seed=seed,
            )

            # Model initialization and training RNG state are
            # independently reset for this variant/seed pair.
            metrics = train_and_evaluate_variant(
                cfg,
                train_loader,
                val_loader,
                epochs=epochs_per_variant,
                device=device,
                seed=seed,
            )

            seed_metrics.append(
                metrics
            )

        # ----------------------------------------------------------
        # Aggregate metrics across seeds
        # ----------------------------------------------------------
        accs = [
            m["accuracy_pct"]
            for m in seed_metrics
        ]

        f1_macros = [
            m["f1_score_macro"]
            for m in seed_metrics
        ]

        f1_weighteds = [
            m["f1_score_weighted"]
            for m in seed_metrics
        ]

        sev_rmses = [
            m["severity_rmse"]
            for m in seed_metrics
        ]

        lead_maes = [
            m["lead_time_mae_hours"]
            for m in seed_metrics
        ]

        last_m = seed_metrics[-1]

        results["variants"][name] = {
            "accuracy_pct_mean": round(
                float(np.mean(accs)),
                2,
            ),
            "accuracy_pct_std": round(
                float(np.std(accs)),
                2,
            ),
            "f1_score_macro_mean": round(
                float(np.mean(f1_macros)),
                4,
            ),
            "f1_score_macro_std": round(
                float(np.std(f1_macros)),
                4,
            ),
            "f1_score_weighted_mean": round(
                float(np.mean(f1_weighteds)),
                4,
            ),
            "f1_score_weighted_std": round(
                float(np.std(f1_weighteds)),
                4,
            ),
            "severity_rmse_mean": round(
                float(np.mean(sev_rmses)),
                4,
            ),
            "severity_rmse_std": round(
                float(np.std(sev_rmses)),
                4,
            ),
            "lead_time_mae_mean": round(
                float(np.mean(lead_maes)),
                4,
            ),
            "lead_time_mae_std": round(
                float(np.std(lead_maes)),
                4,
            ),
            "seed_runs": seed_metrics,
            "confusion_matrix": last_m[
                "confusion_matrix"
            ],
            "evaluation_dataset": last_m[
                "evaluation_dataset"
            ],
            "synthetic_development": True,
            "real_world_validation": False,
            "spectral_stream": cfg[
                "use_spec"
            ],
            "spatial_stream": cfg[
                "use_spat"
            ],
            "env_stream": cfg[
                "use_env"
            ],
        }

        print(
            f"  -> {name} Mean Acc: "
            f"{results['variants'][name]['accuracy_pct_mean']}"
            f"±"
            f"{results['variants'][name]['accuracy_pct_std']}"
            f"% | Mean Macro F1: "
            f"{results['variants'][name]['f1_score_macro_mean']}"
            f"±"
            f"{results['variants'][name]['f1_score_macro_std']}"
        )

    # --------------------------------------------------------------
    # Save report
    # --------------------------------------------------------------
    report_path = os.path.join(
        RESULTS_DIR,
        "ablation_report.json",
    )

    with open(
        report_path,
        "w",
    ) as f:
        json.dump(
            results,
            f,
            indent=2,
        )

    print(
        "\n=== 7-Variant Multi-Seed Ablation "
        "Benchmark Completed! Dynamic results "
        f"saved to {report_path} ==="
    )

    return results


if __name__ == "__main__":
    run_ablation_study()