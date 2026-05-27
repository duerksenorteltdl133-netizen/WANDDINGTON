"""
Self-contained evaluation for perturbation prediction experiments.

No dependencies on sc_agent or the old project. Requires only numpy and scipy.

Metric conventions match MetricComputer from the old project:
- pearson / pearson_de : centroid-level (per-condition mean expression vectors)
- mse / mae            : cell-level (all test non-control cells)
- DE genes             : top-n_de_genes by |centroid_true − ctrl_mean| per condition
                         (falls back to top-n by |centroid_true| when no control given)

Usage
-----
    from simple_eval import evaluate_perturbation, save_metrics

    # predicted_means: {pert_name: np.ndarray (n_genes,)}   ← per-condition centroids
    # observed_means:  {pert_name: np.ndarray (n_genes,)}
    # ctrl_mean:       np.ndarray (n_genes,) or None        ← global control centroid
    metrics = evaluate_perturbation(predicted_means, observed_means, ctrl_mean=ctrl_mean,
                                    model="gears", dataset="norman2019", mode="safe_smoke_run")
    save_metrics(metrics, "results/metrics.json")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import pearsonr


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pearson_1d(a: np.ndarray, b: np.ndarray) -> float | None:
    """Pearson r of two 1-D vectors. Returns None when either is constant."""
    if len(a) < 2 or np.std(a) < 1e-8 or np.std(b) < 1e-8:
        return None
    return float(pearsonr(a, b)[0])


def _top_k_by_abs(arr: np.ndarray, k: int) -> np.ndarray:
    """Indices of the top-k elements by absolute magnitude."""
    n = len(arr)
    if n <= k:
        return np.arange(n)
    return np.argpartition(np.abs(arr), -k)[-k:]


def _nanmean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None and not np.isnan(v)]
    return float(np.mean(vals)) if vals else None


# ── Main evaluator ────────────────────────────────────────────────────────────

def evaluate_perturbation(
    predicted_means: dict[str, np.ndarray],
    observed_means: dict[str, np.ndarray],
    *,
    ctrl_mean: np.ndarray | None = None,
    n_de_genes: int = 20,
    model: str = "unknown",
    dataset: str = "unknown",
    mode: str = "unknown",
) -> dict[str, Any]:
    """
    Compute standardised metrics for perturbation prediction.

    Parameters
    ----------
    predicted_means : {pert_name: mean_expr_vector (n_genes,)}
        Per-condition predicted centroids (mean over predicted cells).
    observed_means : {pert_name: mean_expr_vector (n_genes,)}
        Per-condition observed centroids (mean over true test cells).
    ctrl_mean : np.ndarray (n_genes,), optional
        Global control centroid (mean of all control cells).
        Required for: pearson_delta, pearson_de (canonical), mse_de.
        When None: pearson_de falls back to top-n by |obs| expression.
    n_de_genes : int
        Number of top DE genes per condition (default 20, matching scGPT / GGE).
    model, dataset, mode : metadata fields

    Returns
    -------
    dict with structure:
        primary_metrics:
            pearson          — mean Pearson(pred_centroid, obs_centroid) over conditions
            pearson_de       — pearson restricted to top-n_de_genes DE genes
            pearson_delta    — pearson on (centroid − ctrl_mean) delta vectors [needs ctrl]
            mse              — mean squared error over centroid pairs
            mse_de           — mse restricted to DE genes [needs ctrl]
            mae              — mean absolute error over centroid pairs
        per_perturbation     — per-condition breakdown of the same metrics
        metadata             — model, dataset, n_perturbations_evaluated, mode
    """
    shared = sorted(set(predicted_means) & set(observed_means))
    if not shared:
        raise ValueError("No overlapping perturbation keys between predicted and observed.")

    per_pert: dict[str, dict[str, Any]] = {}
    pearsons, pearsons_de, pearsons_delta = [], [], []
    mses, mses_de, maes = [], [], []

    for key in shared:
        pred = np.asarray(predicted_means[key], dtype=float)
        obs  = np.asarray(observed_means[key],  dtype=float)

        # ── DE gene selection ─────────────────────────────────────────────────
        # Canonical: top-n by |obs − ctrl_mean|; fallback: top-n by |obs|
        if ctrl_mean is not None:
            signal = obs - np.asarray(ctrl_mean, dtype=float)
        else:
            signal = obs
        de_idx = _top_k_by_abs(signal, n_de_genes)

        # ── pearson (centroid level) ──────────────────────────────────────────
        r = _pearson_1d(pred, obs)

        # ── pearson_de ────────────────────────────────────────────────────────
        r_de = _pearson_1d(pred[de_idx], obs[de_idx])

        # ── pearson_delta (requires ctrl) ─────────────────────────────────────
        r_delta: float | None = None
        if ctrl_mean is not None:
            ctrl = np.asarray(ctrl_mean, dtype=float)
            r_delta = _pearson_1d(pred - ctrl, obs - ctrl)

        # ── mse / mae (centroid level) ────────────────────────────────────────
        diff = obs - pred
        mse  = float(np.mean(diff ** 2))
        mae  = float(np.mean(np.abs(diff)))

        # ── mse_de ────────────────────────────────────────────────────────────
        mse_de: float | None = None
        if ctrl_mean is not None:
            diff_de = diff[de_idx]
            mse_de = float(np.mean(diff_de ** 2))

        per_pert[key] = {
            "pearson":       r,
            "pearson_de":    r_de,
            "pearson_delta": r_delta,
            "mse":           mse,
            "mse_de":        mse_de,
            "mae":           mae,
        }

        if r       is not None: pearsons.append(r)
        if r_de    is not None: pearsons_de.append(r_de)
        if r_delta is not None: pearsons_delta.append(r_delta)
        mses.append(mse)
        if mse_de  is not None: mses_de.append(mse_de)
        maes.append(mae)

    primary: dict[str, Any] = {
        "pearson":       _nanmean(pearsons),
        "pearson_de":    _nanmean(pearsons_de),
        "pearson_delta": _nanmean(pearsons_delta),   # None when no ctrl given
        "mse":           _nanmean(mses),
        "mse_de":        _nanmean(mses_de),           # None when no ctrl given
        "mae":           _nanmean(maes),
    }

    return {
        "primary_metrics": primary,
        "per_perturbation": per_pert,
        "metadata": {
            "model":                     model,
            "dataset":                   dataset,
            "n_perturbations_evaluated": len(shared),
            "n_de_genes":                n_de_genes,
            "ctrl_available":            ctrl_mean is not None,
            "mode":                      mode,
        },
    }


def save_metrics(metrics: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(json.dumps(metrics, indent=2))
