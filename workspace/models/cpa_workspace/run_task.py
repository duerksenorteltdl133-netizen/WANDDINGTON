import json
import os
import sys
import traceback
import warnings
from pathlib import Path

os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/numba_cache")
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import anndata as ad
import numpy as np
import pandas as pd
import torch

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path("/home/duanyu/Python/Myproject/single_cell_agent")
WORKSPACE_DIR = Path("/home/duanyu/Python/Myproject/single_cell_agent/workspaces/cpa_workspace")
RESULT_PATH = WORKSPACE_DIR / "results" / "cpa_metrics.json"
DATASET_PATH = Path("/home/duanyu/Python/Myproject/single_cell_agent/data/raw/norman/perturb_processed.h5ad")
USER_REQUEST = "Using the dataset archive at /home/duanyu/Python/Myproject/single_cell_agent/data/raw/norman.zip, use the CPA model to run a safe smoke perturbation prediction test and report metrics."
DATASET_REPORT = "{\n  \"dataset_name\": \"perturb_processed.h5ad\",\n  \"status\": \"success\",\n  \"dimensions\": {\n    \"number_of_cells\": 91205,\n    \"number_of_genes\": 5045\n  },\n  \"metadata_features\": {\n    \"all_obs_columns\": [\n      \"condition\",\n      \"cell_type\",\n      \"dose_val\",\n      \"control\",\n      \"condition_name\"\n    ],\n    \"potential_perturbation_keys\": [\n      \"condition\",\n      \"dose_val\",\n      \"condition_name\"\n    ],\n    \"potential_cell_type_keys\": [\n      \"cell_type\"\n    ]\n  },\n  \"gene_features\": {\n    \"highly_variable_genes_calculated\": false,\n    \"hvg_count\": 0\n  },\n  \"perturbation_preview\": {\n    \"column_used\": \"condition\",\n    \"top_conditions_cell_count\": {\n      \"ctrl\": 7353,\n      \"CEBPE+RUNX1T1\": 1030,\n      \"KLF1+ctrl\": 997,\n      \"TBX3+TBX2\": 969,\n      \"SLC4A1+ctrl\": 853,\n      \"ETS2+CNN1\": 785,\n      \"DUSP9+ETS2\": 698,\n      \"UBASH3B+OSR2\": 677,\n      \"DUSP9+ctrl\": 662,\n      \"ctrl+ETS2\": 656\n    }\n  }\n}"
RUN_MODE = "safe_smoke_run"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "workspaces" / "cpa_workspace"))

import cpa
from sc_agent.tools.evaluation_engine import (
    apply_evaluation_to_payload,
    build_evaluation_record,
    evaluate_condition_predictions,
)


def make_json_safe(value):
    if isinstance(value, dict):
        return {str(k): make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [make_json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def safe_pearson(x, y):
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    if x.size == 0 or y.size == 0:
        return 0.0
    if np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def summarize_predictions(real_adata, generated_by_condition):
    rows = []
    for condition, generated in generated_by_condition.items():
        true_subset = real_adata[real_adata.obs["condition"].astype(str) == str(condition)]
        if len(true_subset) == 0:
            continue
        y_true = np.asarray(true_subset.X.mean(axis=0)).reshape(-1)
        y_pred = np.asarray(generated).mean(axis=0).reshape(-1)
        rows.append(
            {
                "condition": str(condition),
                "pearson": safe_pearson(y_true, y_pred),
                "mse": float(np.mean((y_true - y_pred) ** 2)),
                "n_cells": int(len(true_subset)),
            }
        )
    df = pd.DataFrame(rows)
    metrics = {}
    if not df.empty:
        metrics["pearson"] = float(df["pearson"].mean())
        metrics["mse"] = float(df["mse"].mean())
    return metrics, df


def normalize_condition_text(value: str) -> str:
    parts = [part.strip() for part in str(value).split("+") if part.strip()]
    normalized = []
    for part in parts:
        lowered = part.lower()
        if lowered in {"control", "ctrl", "vehicle", "wt"}:
            normalized.append("ctrl")
        else:
            normalized.append(part)
    if not normalized:
        return "ctrl"
    return "+".join(sorted(normalized))


def build_dummy_dose(condition: str) -> str:
    return "+".join(["1.0" for gene in str(condition).split("+") if gene])


def prepare_user_adata(raw_path: Path):
    adata = ad.read_h5ad(raw_path).copy()
    if "condition" not in adata.obs.columns:
        candidates = ["condition_name", "perturbation", "pert", "guide", "target", "gene"]
        for candidate in candidates:
            if candidate in adata.obs.columns:
                adata.obs["condition"] = adata.obs[candidate].astype(str)
                break
        else:
            raise ValueError("CPA requires a perturbation column such as 'condition'.")

    adata.obs["condition"] = adata.obs["condition"].astype(str).map(normalize_condition_text)
    if "ctrl" not in set(adata.obs["condition"].astype(str)):
        raise ValueError("CPA requires a control condition normalized to 'ctrl'.")

    if "cell_type" not in adata.obs.columns:
        for candidate in ["celltype", "cell_type_name", "cluster"]:
            if candidate in adata.obs.columns:
                adata.obs["cell_type"] = adata.obs[candidate].astype(str)
                break
        else:
            adata.obs["cell_type"] = "unknown"
    adata.obs["cell_type"] = adata.obs["cell_type"].astype(str)

    if "dose_val" not in adata.obs.columns:
        adata.obs["dose_val"] = adata.obs["condition"].astype(str).map(build_dummy_dose)
    else:
        dose_values = adata.obs["dose_val"].astype(str)
        empty_mask = dose_values.isin(["", "nan", "None"])
        dose_values.loc[empty_mask] = adata.obs.loc[empty_mask, "condition"].astype(str).map(build_dummy_dose)
        adata.obs["dose_val"] = dose_values

    adata.obs["split"] = "train"
    adata.obs["control"] = (adata.obs["condition"].astype(str) == "ctrl").astype(int)

    if "gene_name" not in adata.var.columns:
        adata.var["gene_name"] = adata.var_names.astype(str)

    return adata


def assign_condition_splits(adata, n_train, n_valid, n_test):
    perturb_conditions = sorted([c for c in adata.obs["condition"].astype(str).unique().tolist() if c != "ctrl"])
    selected = perturb_conditions[: n_train + n_valid + n_test]
    train_conditions = selected[:n_train]
    valid_conditions = selected[n_train:n_train + n_valid]
    test_conditions = selected[n_train + n_valid:n_train + n_valid + n_test]

    adata = adata[adata.obs["condition"].astype(str).isin(["ctrl"] + selected)].copy()
    condition_series = adata.obs["condition"].astype(str)
    adata.obs.loc[condition_series.isin(train_conditions), "split"] = "train"
    adata.obs.loc[condition_series.isin(valid_conditions), "split"] = "test"
    adata.obs.loc[condition_series.isin(test_conditions), "split"] = "ood"
    adata.obs.loc[condition_series == "ctrl", "split"] = "train"

    return adata, train_conditions, valid_conditions, test_conditions


def subsample_cells(adata, max_ctrl_cells, max_cells_per_condition):
    condition_series = adata.obs["condition"].astype(str)
    keep_indices = adata.obs.index[condition_series == "ctrl"].tolist()[:max_ctrl_cells]
    for condition in sorted([c for c in condition_series.unique().tolist() if c != "ctrl"]):
        keep_indices.extend(adata.obs.index[condition_series == condition].tolist()[:max_cells_per_condition])
    if not keep_indices:
        return adata.copy()
    seen = set()
    ordered = []
    for index in keep_indices:
        if index not in seen:
            ordered.append(index)
            seen.add(index)
    return adata[ordered].copy()


def build_run_profile(adata):
    if RUN_MODE == "full_benchmark_run":
        if not torch.cuda.is_available():
            raise RuntimeError("CPA full_benchmark_run requires CUDA, but cuda:0 is not available.")
        profiled, train_conditions, valid_conditions, test_conditions = assign_condition_splits(
            adata, n_train=96, n_valid=12, n_test=24
        )
        return {
            "adata": subsample_cells(profiled, max_ctrl_cells=2048, max_cells_per_condition=128),
            "device": True,
            "batch_size": 128,
            "max_epochs": 10,
            "n_samples": 20,
            "train_conditions": train_conditions,
            "valid_conditions": valid_conditions,
            "test_conditions": test_conditions,
            "profile": "full_benchmark_run",
        }

    profiled, train_conditions, valid_conditions, test_conditions = assign_condition_splits(
        adata, n_train=8, n_valid=2, n_test=2
    )
    return {
        "adata": subsample_cells(profiled, max_ctrl_cells=256, max_cells_per_condition=32),
        "device": False,
        "batch_size": 64,
        "max_epochs": 2,
        "n_samples": 5,
        "train_conditions": train_conditions,
        "valid_conditions": valid_conditions,
        "test_conditions": test_conditions,
        "profile": "safe_smoke_run",
    }


def make_counterfactual_adata(model_adata, condition, control_pool, cell_type_key="cell_type"):
    true_subset = model_adata[model_adata.obs["condition"].astype(str) == str(condition)].copy()
    if len(true_subset) == 0:
        return None

    if cell_type_key in true_subset.obs.columns and cell_type_key in control_pool.obs.columns:
        target_cell_type = true_subset.obs[cell_type_key].astype(str).mode().iloc[0]
        control_subset = control_pool[control_pool.obs[cell_type_key].astype(str) == str(target_cell_type)].copy()
        if len(control_subset) == 0:
            control_subset = control_pool.copy()
    else:
        control_subset = control_pool.copy()

    if len(control_subset) == 0:
        return None

    replace = len(control_subset) < len(true_subset)
    chosen_idx = np.random.choice(np.arange(len(control_subset)), size=len(true_subset), replace=replace)
    sampled_control = control_subset[chosen_idx].copy()

    feed_adata = true_subset.copy()
    feed_adata.X = sampled_control.X.copy()
    feed_adata.layers["CPA_counterfactual_input"] = sampled_control.X.copy()
    return feed_adata


def main():
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "status": "error",
        "backend_model": "CPA",
        "environment": "cpa_env",
        "run_mode": RUN_MODE,
        "dataset_path": str(DATASET_PATH),
        "user_request": USER_REQUEST,
        "metrics": {},
        "artifacts": {},
    }

    try:
        np.random.seed(42)
        torch.manual_seed(42)

        user_adata = prepare_user_adata(DATASET_PATH)
        profile = build_run_profile(user_adata)
        adata = profile["adata"]

        print(
            f"[CPA] mode={RUN_MODE} | use_gpu={profile['device']} | batch_size={profile['batch_size']} | epochs={profile['max_epochs']}"
        )
        print(f"[CPA] adata shape for run={adata.shape}")

        cpa.CPA.setup_anndata(
            adata,
            perturbation_key="condition",
            control_group="ctrl",
            dosage_key="dose_val",
            is_count_data=False,
            categorical_covariate_keys=["cell_type"],
            max_comb_len=2,
        )

        model = cpa.CPA(
            adata=adata,
            n_latent=64,
            recon_loss="gauss",
            doser_type="logsigm",
            split_key="split",
        )
        model.train(
            max_epochs=profile["max_epochs"],
            use_gpu=profile["device"],
            batch_size=profile["batch_size"],
            plan_kwargs={"lr": 1e-4},
            early_stopping_patience=3,
            check_val_every_n_epoch=1,
            save_path=str(WORKSPACE_DIR / "results" / "cpa_model"),
        )

        control_pool = adata[adata.obs["condition"].astype(str) == "ctrl"].copy()
        generated_by_condition = {}
        for condition in profile["test_conditions"]:
            feed_adata = make_counterfactual_adata(adata, condition, control_pool)
            if feed_adata is None:
                continue
            model.predict(
                adata=feed_adata,
                batch_size=profile["batch_size"],
                n_samples=profile["n_samples"],
                return_mean=True,
            )
            generated_by_condition[condition] = np.asarray(feed_adata.obsm["CPA_pred"])

        test_truth = adata[adata.obs["condition"].astype(str).isin(profile["test_conditions"])].copy()
        gge_truth = adata[
            adata.obs["condition"].astype(str).isin(["ctrl"] + profile["test_conditions"])
        ].copy()
        metrics, per_condition_df = summarize_predictions(test_truth, generated_by_condition)

        gge_summary = evaluate_condition_predictions(
            project_root=PROJECT_ROOT,
            output_dir=WORKSPACE_DIR / "results" / "gge",
            real_adata=gge_truth,
            generated_by_condition=generated_by_condition,
            condition_column="condition",
            control_value="ctrl",
        )

        per_condition_path = WORKSPACE_DIR / "results" / f"cpa_{RUN_MODE}_condition_metrics.csv"
        per_condition_df.to_csv(per_condition_path, index=False)

        payload["status"] = "success"
        payload["metrics"] = make_json_safe(metrics)
        payload["artifacts"] = {
            "workspace": str(WORKSPACE_DIR),
            "condition_metrics_csv": str(per_condition_path),
            "model_dir": str(WORKSPACE_DIR / "results" / "cpa_model"),
        }
        payload["training"] = {
            "device": "cuda:0" if profile["device"] else "cpu",
            "batch_size": profile["batch_size"],
            "epochs": profile["max_epochs"],
            "n_samples": profile["n_samples"],
            "profile": profile["profile"],
        }
        payload["split_summary"] = {
            "train_conditions": profile["train_conditions"],
            "valid_conditions": profile["valid_conditions"],
            "test_conditions": profile["test_conditions"],
            "train_cells": int((adata.obs["split"].astype(str) == "train").sum()),
            "valid_cells": int((adata.obs["split"].astype(str) == "test").sum()),
            "test_cells": int((adata.obs["split"].astype(str) == "ood").sum()),
        }
        payload["per_condition_metrics"] = make_json_safe(
            per_condition_df.to_dict(orient="records")
        )
        payload["evaluation"] = make_json_safe(
            build_evaluation_record(
                native_metrics=metrics,
                gge_summary=gge_summary,
                native_metric_details=per_condition_df.to_dict(orient="records"),
            )
        )
        apply_evaluation_to_payload(payload, payload["evaluation"])
        payload["notes"] = [
            "CPA is executed in cpa_env with NUMBA/MPL temp dirs configured for stable imports.",
            "The controller normalizes the dataset, creates dummy dosages when needed, and uses control cells as counterfactual inputs for held-out perturbations.",
            "Post-training evaluation also runs through the local GGE framework for standardized comparison.",
        ]
    except Exception as exc:
        payload["error"] = str(exc)
        payload["traceback"] = traceback.format_exc()

    with open(RESULT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    if payload["status"] != "success":
        raise SystemExit(payload.get("error", "CPA execution failed"))


if __name__ == "__main__":
    main()
