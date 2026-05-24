from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import anndata as ad

from sc_agent.tools.gge_adapter import (
    create_pair_from_condition_predictions,
    create_pair_from_prediction_arrays,
    run_gge_evaluation,
)


DEFAULT_GGE_METRIC_ALIASES = {
    "pearson_mean": "pearson",
    "spearman_mean": "spearman",
    "mse_mean": "mse",
    "r_squared_mean": "r_squared",
}


class GGEBlock(TypedDict):
    status: str | None
    raw_test_aggregates: dict[str, Any]
    deg_test_aggregates: dict[str, Any]
    deg_gene_count: int | None
    summary: dict[str, Any]


class EvaluationRecord(TypedDict):
    primary_metrics: dict[str, Any]
    """Best available metrics for cross-backend comparison.
    Priority: shared (MetricComputer) > GGE aliases > native."""
    native_metrics: dict[str, Any]
    """Backend-specific metrics kept as supplemental diagnostics."""
    shared_metrics: dict[str, Any]
    """Full SharedMetrics output from MetricComputer, including provenance."""
    native_metric_details: Any
    gge: GGEBlock


def build_evaluation_record(
    *,
    native_metrics: dict[str, Any] | None,
    gge_summary: dict[str, Any] | None,
    shared_metrics: dict[str, Any] | None = None,
    native_metric_details: Any | None = None,
    gge_metric_aliases: dict[str, str] | None = None,
    prefer_existing_native_metrics: bool = True,
) -> EvaluationRecord:
    """
    Build a structured EvaluationRecord with three-tier metric priority.

    Priority for primary_metrics (highest wins):
      1. shared_metrics (MetricComputer — deterministic, cross-backend)
      2. GGE aliases     (standardised external framework)
      3. native_metrics  (backend-specific, supplemental)

    The `shared_metrics` parameter is optional; omitting it preserves the
    previous behaviour exactly (GGE aliases on top of native).
    """
    from sc_agent.tools.metrics import extract_scalar_metrics

    # Base: native → overwrite with GGE aliases (existing behaviour)
    merged_primary = merge_gge_metrics(
        native_metrics or {},
        gge_summary or {},
        aliases=gge_metric_aliases,
        prefer_existing=prefer_existing_native_metrics,
    )
    # Highest priority: shared scalar metrics overwrite everything
    if shared_metrics:
        merged_primary.update(extract_scalar_metrics(shared_metrics))

    gge_summary = gge_summary or {}
    gge: GGEBlock = {
        "status": gge_summary.get("status"),
        "raw_test_aggregates": gge_summary.get("raw_test_aggregates", {}),
        "deg_test_aggregates": gge_summary.get("deg_test_aggregates", {}),
        "deg_gene_count": gge_summary.get("deg_gene_count"),
        "summary": gge_summary,
    }
    return EvaluationRecord(
        primary_metrics=merged_primary,
        native_metrics=native_metrics or {},
        shared_metrics=shared_metrics or {},
        native_metric_details=native_metric_details,
        gge=gge,
    )


def apply_evaluation_to_payload(
    payload: dict[str, Any],
    evaluation: EvaluationRecord | dict[str, Any] | None,
    *,
    metrics_key: str = "metrics",
    gge_key: str = "gge_evaluation",
    prefer_native_metrics: bool = True,
) -> dict[str, Any]:
    evaluation = evaluation or {}
    payload["evaluation"] = evaluation

    primary_metrics = evaluation.get("primary_metrics", {}) if isinstance(evaluation, dict) else {}
    native_metrics = evaluation.get("native_metrics", {}) if isinstance(evaluation, dict) else {}
    gge_summary = (
        evaluation.get("gge", {}).get("summary", {})
        if isinstance(evaluation, dict)
        else {}
    )

    if prefer_native_metrics and native_metrics:
        payload[metrics_key] = native_metrics
    else:
        payload[metrics_key] = primary_metrics or native_metrics

    payload[gge_key] = gge_summary
    return payload


def merge_gge_metrics(
    metrics: dict[str, Any] | None,
    gge_summary: dict[str, Any] | None,
    *,
    aliases: dict[str, str] | None = None,
    prefer_existing: bool = True,
) -> dict[str, Any]:
    merged = dict(metrics or {})
    if not gge_summary:
        return merged

    raw_aggregates = gge_summary.get("raw_test_aggregates", {})
    alias_map = aliases or DEFAULT_GGE_METRIC_ALIASES
    for source_key, target_key in alias_map.items():
        if source_key not in raw_aggregates:
            continue
        if prefer_existing and target_key in merged and merged[target_key] is not None:
            continue
        merged[target_key] = raw_aggregates[source_key]
    return merged


def evaluate_prediction_arrays(
    *,
    project_root: Path,
    output_dir: Path,
    truth_matrix: Any,
    pred_matrix: Any,
    pert_categories: list[str] | Any,
    gene_names: list[str],
    control_matrix: Any | None = None,
    condition_column: str = "condition",
    split_column: str = "split",
    control_value: str = "ctrl",
    verbose: bool = False,
) -> dict[str, Any]:
    gge_real, gge_generated = create_pair_from_prediction_arrays(
        truth_matrix=truth_matrix,
        pred_matrix=pred_matrix,
        pert_categories=pert_categories,
        gene_names=gene_names,
        control_matrix=control_matrix,
        condition_column=condition_column,
        split_column=split_column,
        control_value=control_value,
    )
    return run_gge_evaluation(
        project_root=project_root,
        real_adata=gge_real,
        generated_adata=gge_generated,
        output_dir=output_dir,
        condition_column=condition_column,
        split_column=split_column,
        control_value=control_value,
        verbose=verbose,
    )


def evaluate_condition_predictions(
    *,
    project_root: Path,
    output_dir: Path,
    real_adata: ad.AnnData,
    generated_by_condition: dict[str, Any],
    condition_column: str = "condition",
    split_column: str = "split",
    control_value: str = "ctrl",
    verbose: bool = False,
) -> dict[str, Any]:
    gge_real, gge_generated = create_pair_from_condition_predictions(
        real_adata=real_adata,
        generated_by_condition=generated_by_condition,
        condition_column=condition_column,
        split_column=split_column,
        control_value=control_value,
    )
    return run_gge_evaluation(
        project_root=project_root,
        real_adata=gge_real,
        generated_adata=gge_generated,
        output_dir=output_dir,
        condition_column=condition_column,
        split_column=split_column,
        control_value=control_value,
        verbose=verbose,
    )


def evaluate_prediction_artifact(
    artifact: "Any",
    *,
    project_root: Path,
    output_dir: Path,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run the full GGE evaluation pipeline from a PredictionArtifact.

    Drop-in replacement for evaluate_prediction_arrays() and
    evaluate_condition_predictions() — accepts any backend output that has
    been wrapped in the unified contract.

    Example
    -------
    artifact = PredictionArtifact.from_arrays(
        y_true=truth, y_pred=pred,
        gene_names=gene_names,
        condition_labels=conditions,
        backend_name="scgpt",
    )
    gge_summary = evaluate_prediction_artifact(
        artifact,
        project_root=PROJECT_ROOT,
        output_dir=WORKSPACE_DIR / "results" / "gge",
    )
    evaluation = build_evaluation_record(
        native_metrics=native_metrics,
        gge_summary=gge_summary,
    )
    """
    # Deferred import avoids a circular dependency at module load time.
    from sc_agent.tools.prediction_artifact import PredictionArtifact

    if not isinstance(artifact, PredictionArtifact):
        raise TypeError(
            f"evaluate_prediction_artifact() expects a PredictionArtifact, "
            f"got {type(artifact).__name__}."
        )

    artifact.validate()
    real_adata, generated_adata = artifact.to_gge_inputs()
    control_value = artifact.control_labels[0] if artifact.control_labels else "ctrl"

    return run_gge_evaluation(
        project_root=project_root,
        real_adata=real_adata,
        generated_adata=generated_adata,
        output_dir=output_dir,
        condition_column=artifact.condition_column,
        split_column=artifact.split_column,
        control_value=control_value,
        verbose=verbose,
    )


def compute_and_evaluate(
    artifact: "Any",
    *,
    project_root: Path,
    output_dir: Path,
    native_metrics: dict[str, Any] | None = None,
    native_metric_details: Any | None = None,
    run_gge: bool = True,
    metric_computer: "Any | None" = None,
    verbose: bool = False,
) -> EvaluationRecord:
    """
    Full evaluation pipeline for a PredictionArtifact — recommended entry
    point for backends that have adopted the contract.

    Steps
    -----
    1. MetricComputer.compute(artifact)     → shared_metrics
    2. (optional) evaluate_prediction_artifact() → gge_summary
    3. build_evaluation_record(shared_metrics=…)  → EvaluationRecord

    The returned record has three-tier priority in primary_metrics:
      shared (deterministic, cross-backend) > GGE > native.

    Parameters
    ----------
    artifact          PredictionArtifact produced by the backend.
    project_root      Path to the repository root (needed by GGE).
    output_dir        Directory for GGE artefacts (ignored when run_gge=False).
    native_metrics    Backend-specific metrics to carry forward as supplemental.
    native_metric_details  Any per-gene / per-condition detail structure.
    run_gge           Whether to invoke the GGE evaluation framework.
                      Set False for unit tests or offline environments.
    metric_computer   Custom MetricComputer instance (uses default if None).
    verbose           Passed through to GGE.

    Example
    -------
    artifact = PredictionArtifact.from_arrays(
        y_true=truth, y_pred=pred,
        gene_names=gene_names, condition_labels=conds,
        backend_name="scgpt", dataset_path=str(dataset_path),
    )
    evaluation = compute_and_evaluate(
        artifact,
        project_root=PROJECT_ROOT,
        output_dir=WORKSPACE_DIR / "results" / "gge",
        native_metrics={"pearson": 0.91, "pearson_de": 0.85},
    )
    payload["evaluation"] = evaluation
    apply_evaluation_to_payload(payload, evaluation)
    """
    from sc_agent.tools.prediction_artifact import PredictionArtifact
    from sc_agent.tools.metrics import MetricComputer

    if not isinstance(artifact, PredictionArtifact):
        raise TypeError(
            f"compute_and_evaluate() expects a PredictionArtifact, "
            f"got {type(artifact).__name__}."
        )

    # Step 1 — unified shared metrics
    mc = metric_computer if metric_computer is not None else MetricComputer()
    shared = dict(mc.compute(artifact))

    # Step 2 — GGE (optional, may be unavailable offline)
    gge_summary: dict[str, Any] = {}
    if run_gge:
        try:
            gge_summary = evaluate_prediction_artifact(
                artifact,
                project_root=project_root,
                output_dir=output_dir,
                verbose=verbose,
            )
        except Exception as exc:
            gge_summary = {"status": "error", "reason": str(exc)}

    # Step 3 — build unified record
    return build_evaluation_record(
        native_metrics=native_metrics,
        gge_summary=gge_summary,
        shared_metrics=shared,
        native_metric_details=native_metric_details,
    )
