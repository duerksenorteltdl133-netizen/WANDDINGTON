"""result_summary — structured summary and interpretation of a backend result JSON.

Env vars:
  SC_RESULT_PATH   path to a backend result JSON (required)
"""
import json
import os
import sys
from pathlib import Path

SC_RESULT_PATH = os.environ.get("SC_RESULT_PATH", "")

if not SC_RESULT_PATH or not Path(SC_RESULT_PATH).exists():
    print("Error: SC_RESULT_PATH not set or file not found.")
    sys.exit(1)

result = json.loads(Path(SC_RESULT_PATH).read_text(encoding="utf-8"))

backend    = result.get("backend", "unknown")
status     = result.get("status", "unknown")
evaluation = result.get("evaluation", {})
primary    = evaluation.get("primary_metrics", {})
native     = evaluation.get("native_metrics", {})
gge        = evaluation.get("gge", {})

print(f"# Result Summary — {backend}")
print(f"\n**Status**: `{status}`")

if result.get("error"):
    print(f"\n**Error**: {result['error']}")

# Primary metrics
if primary:
    print("\n## Primary Metrics\n")
    print(f"{'Metric':<30} {'Value':>10}")
    print("-" * 42)
    for k, v in primary.items():
        if isinstance(v, float):
            print(f"{k:<30} {v:>10.4f}")
        elif v is not None:
            print(f"{k:<30} {str(v):>10}")

# Interpretation
pearson = primary.get("pearson") or primary.get("pearson_mean")
mse     = primary.get("mse")     or primary.get("mse_mean")
r2      = primary.get("r2")      or primary.get("r2_mean")

print("\n## Interpretation\n")
if pearson is not None:
    if pearson > 0.7:
        quality = "**strong**"
        desc = "Predictions closely track ground truth gene expression changes."
    elif pearson > 0.4:
        quality = "**moderate**"
        desc = "Model captures the general direction of perturbation responses."
    elif pearson > 0.1:
        quality = "**weak**"
        desc = "Model provides limited predictive signal above baseline."
    else:
        quality = "**near-baseline**"
        desc = "Predictions show little correlation with ground truth."
    print(f"- Pearson correlation is {quality} ({pearson:.4f}). {desc}")

if mse is not None:
    print(f"- MSE = {mse:.4f}. Lower is better; compare against non-control mean baseline.")

if r2 is not None:
    if r2 < 0:
        print(f"- R² = {r2:.4f}. Negative R² means the model performs worse than a constant prediction.")
    else:
        print(f"- R² = {r2:.4f}. Fraction of variance in gene expression changes explained by the model.")

# DE-gene metrics
pearson_de = primary.get("pearson_de") or primary.get("pearson_de_mean")
mse_de     = primary.get("mse_de")     or primary.get("mse_de_mean")
if pearson_de is not None or mse_de is not None:
    print("\n### Top Differentially Expressed Genes\n")
    if pearson_de is not None:
        print(f"- Pearson-DE = {pearson_de:.4f} (correlation restricted to top DE genes; harder task)")
    if mse_de is not None:
        print(f"- MSE-DE     = {mse_de:.4f}")

# GGE aggregates
raw = (gge or {}).get("raw_test_aggregates", {})
deg = (gge or {}).get("deg_test_aggregates", {})
if raw:
    print("\n## GGE Raw Aggregates\n")
    for k, v in raw.items():
        if isinstance(v, float):
            print(f"- {k}: {v:.4f}")
if deg:
    print("\n## GGE DEG Aggregates\n")
    for k, v in deg.items():
        if isinstance(v, float):
            print(f"- {k}: {v:.4f}")

# Native metrics (model-specific)
if native:
    print("\n## Native Metrics (model-specific)\n")
    for k, v in native.items():
        if isinstance(v, float):
            print(f"- {k}: {v:.4f}")
        elif v is not None:
            print(f"- {k}: {v}")
