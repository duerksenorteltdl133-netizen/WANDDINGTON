"""model_comparison — compare two or more backend result JSONs side by side.

Env vars:
  SC_RESULT_PATHS  comma-separated paths to backend result JSONs (required, ≥2)

Falls back to SC_RESULT_PATH if SC_RESULT_PATHS is not set.
"""
import json
import os
import sys
from pathlib import Path

paths_str = os.environ.get("SC_RESULT_PATHS", "") or os.environ.get("SC_RESULT_PATH", "")
if not paths_str:
    print("Error: SC_RESULT_PATHS not set. Provide comma-separated paths to result JSONs.")
    sys.exit(1)

paths = [Path(p.strip()) for p in paths_str.split(",") if p.strip()]
paths = [p for p in paths if p.exists()]
if not paths:
    print("Error: None of the provided result paths exist.")
    sys.exit(1)

results = []
for p in paths:
    try:
        results.append(json.loads(p.read_text(encoding="utf-8")))
    except Exception as exc:
        print(f"Warning: could not read {p}: {exc}")

if not results:
    print("Error: No valid result files loaded.")
    sys.exit(1)

METRICS = ["pearson", "pearson_mean", "mse", "mse_mean", "r2", "r2_mean",
           "pearson_de", "pearson_de_mean", "mse_de", "mse_de_mean"]


def _get(result: dict, key: str):
    primary = result.get("evaluation", {}).get("primary_metrics", {})
    return primary.get(key) or primary.get(key.replace("_mean", ""))


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


# Collect all present metric keys across all results
present = []
for m in METRICS:
    if any(_get(r, m) is not None for r in results):
        label = m.replace("_mean", "")
        if label not in present:
            present.append(label)

print("# Model Comparison\n")

# Header
col_w = 14
name_w = 22
header_parts = [f"{'Metric':<{name_w}}"]
backends = []
for r in results:
    b = r.get("backend", "unknown")
    backends.append(b)
    header_parts.append(f"{b[:col_w]:>{col_w}}")
print("  ".join(header_parts))
print("-" * (name_w + (col_w + 2) * len(results)))

for m in present:
    row = [f"{m:<{name_w}}"]
    vals = [_get(r, m) for r in results]
    # Find best (highest for pearson/r2, lowest for mse)
    numeric = [v for v in vals if isinstance(v, float)]
    is_lower_better = "mse" in m
    best = min(numeric) if (is_lower_better and numeric) else (max(numeric) if numeric else None)
    for v in vals:
        cell = _fmt(v)
        if isinstance(v, float) and v == best and len(numeric) > 1:
            cell = f"*{cell}*"   # mark best
        row.append(f"{cell:>{col_w}}")
    print("  ".join(row))

print("\n_Asterisk (*) marks the best value per metric._")

# Status summary
print("\n## Status\n")
for b, r in zip(backends, results):
    status = r.get("status", "unknown")
    err    = r.get("error", "")
    line   = f"- **{b}**: `{status}`"
    if err:
        line += f" — {err[:80]}"
    print(line)

# Delta table (only when exactly 2 models)
if len(results) == 2:
    print("\n## Delta (second − first)\n")
    b0, b1 = backends[0], backends[1]
    print(f"Positive = {b1} better; Negative = {b0} better.\n")
    for m in present:
        v0, v1 = _get(results[0], m), _get(results[1], m)
        if isinstance(v0, float) and isinstance(v1, float):
            delta = v1 - v0
            direction = "↑" if delta > 0 else "↓"
            better = b1 if (delta > 0 and "mse" not in m) or (delta < 0 and "mse" in m) else b0
            print(f"- {m}: {delta:+.4f} {direction}  (better: {better})")
